import os
import sys
import uuid
from concurrent import futures

import grpc

from app.database import SessionLocal
from app.events import publish_event
from app.models import GoalOperation, SavingsGoal


sys.path.append(os.path.dirname(__file__))

import savings_pb2
import savings_pb2_grpc


GRPC_PORT = int(os.getenv("SAVINGS_GRPC_PORT", "50052"))

_grpc_server = None


def _datetime_to_string(value):
    if not value:
        return ""
    return value.isoformat()


def _operation_to_response(operation: GoalOperation) -> savings_pb2.GoalOperationResponse:
    return savings_pb2.GoalOperationResponse(
        id=operation.id,
        user_id=operation.user_id,
        goal_id=operation.goal_id,
        operation_type=operation.operation_type,
        amount=float(operation.amount),
        status=operation.status,
        failure_reason=operation.failure_reason or "",
        created_at=_datetime_to_string(operation.created_at),
        processed_at=_datetime_to_string(operation.processed_at),
        transport="grpc",
    )


class SavingsGrpcService(savings_pb2_grpc.SavingsServiceServicer):
    def CreateGoalOperation(self, request, context):
        db = SessionLocal()

        try:
            goal = (
                db.query(SavingsGoal)
                .filter(SavingsGoal.id == request.goal_id)
                .first()
            )

            if not goal or goal.status == "DELETED":
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("Savings goal not found")
                return savings_pb2.GoalOperationResponse()

            if request.amount <= 0:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Amount must be positive")
                return savings_pb2.GoalOperationResponse()

            operation_type = (request.operation_type or "").upper()

            if operation_type not in ["DEPOSIT", "WITHDRAW"]:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Operation type must be either DEPOSIT or WITHDRAW")
                return savings_pb2.GoalOperationResponse()

            # If user_id is not sent, use the goal owner.
            # This keeps the gRPC method compatible with simple callers.
            operation_user_id = request.user_id or goal.user_id

            if operation_user_id != goal.user_id:
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Operation user does not match goal owner")
                return savings_pb2.GoalOperationResponse()

            operation = GoalOperation(
                id=str(uuid.uuid4()),
                user_id=operation_user_id,
                goal_id=goal.id,
                operation_type=operation_type,
                amount=float(request.amount),
                status="PENDING",
                failure_reason=None,
            )

            db.add(operation)
            db.commit()
            db.refresh(operation)

            publish_event(
                topic="goal.operation.created",
                key=operation.user_id,
                event={
                    "event_type": "goal.operation.created",
                    "operation_id": operation.id,
                    "goal_id": goal.id,
                    "goal_title": goal.title,
                    "user_id": operation.user_id,
                    "operation_type": operation.operation_type,
                    "amount": operation.amount,
                    "status": operation.status,
                },
            )

            return _operation_to_response(operation)

        except Exception as error:
            db.rollback()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(error))
            return savings_pb2.GoalOperationResponse()

        finally:
            db.close()


def start_grpc_server():
    global _grpc_server

    if _grpc_server is not None:
        return

    _grpc_server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    savings_pb2_grpc.add_SavingsServiceServicer_to_server(
        SavingsGrpcService(),
        _grpc_server,
    )

    _grpc_server.add_insecure_port(f"0.0.0.0:{GRPC_PORT}")
    _grpc_server.start()

    print(f"[gRPC] SavingsService started on port {GRPC_PORT}")


def stop_grpc_server():
    global _grpc_server

    if _grpc_server is not None:
        _grpc_server.stop(grace=3)
        _grpc_server = None
        print("[gRPC] SavingsService stopped")
