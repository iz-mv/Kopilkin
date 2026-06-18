import os
import sys

import grpc


sys.path.append(os.path.dirname(__file__))

import transaction_pb2
import transaction_pb2_grpc
import savings_pb2
import savings_pb2_grpc


TRANSACTION_GRPC_TARGET = os.getenv(
    "TRANSACTION_GRPC_TARGET",
    "transaction-service:50051",
)

SAVINGS_GRPC_TARGET = os.getenv(
    "SAVINGS_GRPC_TARGET",
    "savings-service:50052",
)


def get_user_summary_via_grpc(user_id: str) -> dict:
    with grpc.insecure_channel(TRANSACTION_GRPC_TARGET) as channel:
        stub = transaction_pb2_grpc.TransactionServiceStub(channel)

        response = stub.GetUserSummary(
            transaction_pb2.UserSummaryRequest(user_id=user_id),
            timeout=5,
        )

    return {
        "user_id": response.user_id,
        "total_income": response.income,
        "total_expense": response.expense,
        "balance": response.balance,
        "transactions_count": 0,
        "transport": "grpc",
    }

def create_goal_operation_via_grpc(
    goal_id: str,
    user_id: str,
    operation_type: str,
    amount: float,
) -> dict:
    with grpc.insecure_channel(SAVINGS_GRPC_TARGET) as channel:
        stub = savings_pb2_grpc.SavingsServiceStub(channel)

        response = stub.CreateGoalOperation(
            savings_pb2.CreateGoalOperationRequest(
                goal_id=goal_id,
                user_id=user_id or "",
                operation_type=operation_type,
                amount=float(amount),
            ),
            timeout=10,
        )

    return {
        "id": response.id,
        "user_id": response.user_id,
        "goal_id": response.goal_id,
        "operation_type": response.operation_type,
        "amount": response.amount,
        "status": response.status,
        "failure_reason": response.failure_reason or None,
        "created_at": response.created_at or None,
        "processed_at": response.processed_at or None,
        "transport": response.transport or "grpc",
    }
