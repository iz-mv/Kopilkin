import os
import sys
from concurrent import futures

import grpc

from app.cache import get_cache, set_cache
from app.database import SessionLocal
from app.models import Transaction


sys.path.append(os.path.dirname(__file__))

import transaction_pb2
import transaction_pb2_grpc


GRPC_PORT = int(os.getenv("TRANSACTION_GRPC_PORT", "50051"))

_grpc_server = None


class TransactionGrpcService(transaction_pb2_grpc.TransactionServiceServicer):
    def GetUserSummary(self, request, context):
        user_id = request.user_id

        db = SessionLocal()

        try:
            cache_key = f"summary:{user_id}"

            cached_summary = get_cache(cache_key)

            if cached_summary:
                return transaction_pb2.UserSummaryResponse(
                    user_id=cached_summary["user_id"],
                    income=float(cached_summary["total_income"]),
                    expense=float(cached_summary["total_expense"]),
                    balance=float(cached_summary["balance"]),
                )

            transactions = (
                db.query(Transaction)
                .filter(Transaction.user_id == user_id)
                .all()
            )

            total_income = sum(
                transaction.amount
                for transaction in transactions
                if transaction.type == "income"
            )

            total_expense = sum(
                transaction.amount
                for transaction in transactions
                if transaction.type == "expense"
            )

            balance = total_income - total_expense

            summary = {
                "user_id": user_id,
                "total_income": total_income,
                "total_expense": total_expense,
                "balance": balance,
                "transactions_count": len(transactions),
            }

            set_cache(cache_key, summary, ttl_seconds=60)

            return transaction_pb2.UserSummaryResponse(
                user_id=user_id,
                income=float(total_income),
                expense=float(total_expense),
                balance=float(balance),
            )

        except Exception as error:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(error))

            return transaction_pb2.UserSummaryResponse(
                user_id=user_id,
                income=0,
                expense=0,
                balance=0,
            )

        finally:
            db.close()


def start_grpc_server():
    global _grpc_server

    if _grpc_server is not None:
        return

    _grpc_server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10)
    )

    transaction_pb2_grpc.add_TransactionServiceServicer_to_server(
        TransactionGrpcService(),
        _grpc_server,
    )

    _grpc_server.add_insecure_port(f"0.0.0.0:{GRPC_PORT}")
    _grpc_server.start()

    print(f"[gRPC] TransactionService started on port {GRPC_PORT}")


def stop_grpc_server():
    global _grpc_server

    if _grpc_server is not None:
        _grpc_server.stop(grace=3)
        _grpc_server = None
        print("[gRPC] TransactionService stopped")