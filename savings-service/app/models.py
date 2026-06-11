from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime

from app.database import Base


class SavingsGoal(Base):
    __tablename__ = "savings_goals"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)

    title = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0.0)
    image_url = Column(String, nullable=True)
    status = Column(String, default="ACTIVE", nullable=False)  # ACTIVE/COMPLETED/DELETED

    created_at = Column(DateTime, default=datetime.utcnow)


class GoalOperation(Base):
    __tablename__ = "goal_operations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    goal_id = Column(String, index=True, nullable=False)

    # DEPOSIT = put money into the goal
    # WITHDRAW = take money back from the goal
    operation_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)

    # PENDING -> PROCESSING -> CONFIRMED/FAILED/CANCELLED
    status = Column(String, index=True, default="PENDING", nullable=False)
    failure_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
