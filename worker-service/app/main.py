import json
import os
import time
from datetime import datetime, date
from typing import Optional

import redis
import requests
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from sqlalchemy import Column, DateTime, Float, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SAVINGS_DATABASE_URL = os.getenv(
    "SAVINGS_DATABASE_URL",
    "postgresql://kopilkin:kopilkin_password@localhost:5432/savings_db",
)
TRANSACTION_SERVICE_URL = os.getenv(
    "TRANSACTION_SERVICE_URL",
    "http://localhost:8002",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

Base = declarative_base()


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    image_url = Column(String, nullable=True)
    status = Column(String, default="ACTIVE", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GoalOperation(Base):
    __tablename__ = "goal_operations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    goal_id = Column(String, index=True, nullable=False)
    operation_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, index=True, default="PENDING", nullable=False)
    failure_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


engine = create_engine(SAVINGS_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def get_consumer() -> KafkaConsumer:
    while True:
        try:
            consumer = KafkaConsumer(
                "goal.operation.created",
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id="kopilkin-goal-operation-worker",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda value: json.loads(value.decode("utf-8")),
                key_deserializer=lambda key: key.decode("utf-8") if key else None,
            )
            print("[Worker] Connected to Kafka and subscribed to goal.operation.created")
            return consumer
        except NoBrokersAvailable:
            print("[Worker] Kafka is not ready yet. Retrying in 3 seconds...")
            time.sleep(3)


def acquire_goal_lock(goal_id: str, ttl_seconds: int = 15) -> bool:
    lock_key = f"lock:goal:{goal_id}"
    return bool(redis_client.set(lock_key, "1", nx=True, ex=ttl_seconds))


def release_goal_lock(goal_id: str) -> None:
    redis_client.delete(f"lock:goal:{goal_id}")


def create_transaction_for_operation(goal: SavingsGoal, operation: GoalOperation) -> None:
    transaction_id = f"tx-goal-operation-{operation.id}"

    if operation.operation_type == "DEPOSIT":
        transaction_type = "expense"
        category = "Savings Goal"
        description = f"Saved for goal: {goal.title}"
    else:
        transaction_type = "income"
        category = "Savings Withdrawal"
        description = f"Withdrawn from goal: {goal.title}"

    payload = {
        "id": transaction_id,
        "user_id": operation.user_id,
        "amount": operation.amount,
        "category": category,
        "type": transaction_type,
        "description": description,
        "date": date.today().isoformat(),
    }

    response = requests.post(
        f"{TRANSACTION_SERVICE_URL}/transactions",
        json=payload,
        timeout=10,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Transaction service failed with status={response.status_code}, body={response.text}"
        )

    print(
        f"[Worker] Transaction created/confirmed for operation={operation.id}, "
        f"transaction_id={transaction_id}"
    )


def process_goal_operation(operation_id: str) -> None:
    db: Optional[Session] = None

    try:
        db = SessionLocal()

        operation = (
            db.query(GoalOperation)
            .filter(GoalOperation.id == operation_id)
            .first()
        )

        if not operation:
            print(f"[Worker] Operation not found: {operation_id}")
            return

        if operation.status == "CONFIRMED":
            print(f"[Worker] Operation already confirmed: {operation_id}")
            return

        if operation.status in ["FAILED", "CANCELLED"]:
            print(f"[Worker] Operation already finished with status={operation.status}: {operation_id}")
            return

        goal = db.query(SavingsGoal).filter(SavingsGoal.id == operation.goal_id).first()

        if not goal or goal.status == "DELETED":
            operation.status = "FAILED"
            operation.failure_reason = "Savings goal not found"
            operation.processed_at = datetime.utcnow()
            db.commit()
            print(f"[Worker] Goal not found for operation={operation_id}")
            return

        if not acquire_goal_lock(goal.id):
            print(f"[Worker] Goal is locked, will retry later: goal={goal.id}, operation={operation.id}")
            # raising makes this message not fully processed in our logic, but Kafka auto-commit may still move on.
            return

        try:
            operation.status = "PROCESSING"
            operation.failure_reason = None
            db.commit()

            if operation.operation_type == "DEPOSIT":
                goal.current_amount += operation.amount
            elif operation.operation_type == "WITHDRAW":
                if operation.amount > goal.current_amount:
                    operation.status = "FAILED"
                    operation.failure_reason = "Not enough saved amount"
                    operation.processed_at = datetime.utcnow()
                    db.commit()
                    print(f"[Worker] Withdraw failed: not enough amount, operation={operation.id}")
                    return

                goal.current_amount -= operation.amount
            else:
                operation.status = "FAILED"
                operation.failure_reason = f"Unknown operation type: {operation.operation_type}"
                operation.processed_at = datetime.utcnow()
                db.commit()
                print(f"[Worker] Unknown operation type for operation={operation.id}")
                return

            if goal.current_amount >= goal.target_amount:
                goal.status = "COMPLETED"
            elif goal.status == "COMPLETED" and goal.current_amount < goal.target_amount:
                goal.status = "ACTIVE"

            create_transaction_for_operation(goal=goal, operation=operation)

            operation.status = "CONFIRMED"
            operation.processed_at = datetime.utcnow()
            operation.failure_reason = None

            db.commit()

            print(
                f"[Worker] Operation confirmed: {operation.id}, "
                f"type={operation.operation_type}, amount={operation.amount}, goal={goal.id}"
            )
        finally:
            release_goal_lock(goal.id)

    except Exception as error:
        print(f"[Worker] Failed to process operation={operation_id}: {error}")

        if db:
            try:
                operation = (
                    db.query(GoalOperation)
                    .filter(GoalOperation.id == operation_id)
                    .first()
                )
                if operation and operation.status not in ["CONFIRMED", "CANCELLED"]:
                    operation.status = "FAILED"
                    operation.failure_reason = str(error)[:250]
                    operation.processed_at = datetime.utcnow()
                    db.commit()
            except Exception as db_error:
                print(f"[Worker] Failed to mark operation as FAILED: {db_error}")
    finally:
        if db:
            db.close()


def main() -> None:
    print("[Worker] Kopilkin worker-service started")
    Base.metadata.create_all(bind=engine)

    consumer = get_consumer()

    for message in consumer:
        event = message.value
        event_type = event.get("event_type")
        operation_id = event.get("operation_id")

        print(f"[Worker] Received event: {event}")

        if event_type != "goal.operation.created" or not operation_id:
            print("[Worker] Ignored unsupported event")
            continue

        process_goal_operation(operation_id)


if __name__ == "__main__":
    main()
