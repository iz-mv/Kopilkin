import os
import sys

import grpc


sys.path.append(os.path.dirname(__file__))

import transaction_pb2
import transaction_pb2_grpc


TRANSACTION_GRPC_TARGET = os.getenv(
    "TRANSACTION_GRPC_TARGET",
    "transaction-service:50051",
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