import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.cache import delete_cache, get_cache, set_cache
from app.events import publish_event
from app.models import Transaction
from app.schemas import TransactionCreate


ALLOWED_TRANSACTION_TYPES = {"income", "expense"}


def create_transaction_logic(data: TransactionCreate, db: Session) -> Transaction:
    if data.type not in ALLOWED_TRANSACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Transaction type must be either 'income' or 'expense'",
        )

    transaction_id = data.id or str(uuid.uuid4())

    # Idempotency: if another service retries the same request with the same id,
    # return the existing transaction instead of creating a duplicate.
    existing_transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if existing_transaction:
        return existing_transaction

    transaction = Transaction(
        id=transaction_id,
        user_id=data.user_id,
        amount=data.amount,
        category=data.category,
        type=data.type,
        description=data.description,
        date=data.date,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    publish_event(
        topic="transaction.created",
        key=transaction.user_id,
        event={
            "event_type": "transaction.created",
            "transaction_id": transaction.id,
            "user_id": transaction.user_id,
            "amount": transaction.amount,
            "category": transaction.category,
            "type": transaction.type,
            "description": transaction.description,
            "date": transaction.date,
        },
    )

    # The financial summary changed, so the old Redis cache must be removed.
    delete_cache(f"summary:{transaction.user_id}")

    return transaction


def get_user_transactions_logic(user_id: str, db: Session) -> list[Transaction]:
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )


def get_user_summary_logic(user_id: str, db: Session) -> dict:
    cache_key = f"summary:{user_id}"

    cached_summary = get_cache(cache_key)
    if cached_summary:
        return cached_summary

    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .all()
    )

    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    balance = total_income - total_expense

    summary = {
        "user_id": user_id,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "transactions_count": len(transactions),
    }

    # Store summary in Redis for 60 seconds.
    set_cache(cache_key, summary, ttl_seconds=60)

    return summary


def delete_transaction_logic(transaction_id: str, db: Session) -> dict:
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    deleted_event = {
        "event_type": "transaction.deleted",
        "transaction_id": transaction.id,
        "user_id": transaction.user_id,
        "amount": transaction.amount,
        "category": transaction.category,
        "type": transaction.type,
        "description": transaction.description,
        "date": transaction.date,
    }

    db.delete(transaction)
    db.commit()

    publish_event(
        topic="transaction.deleted",
        key=deleted_event["user_id"],
        event=deleted_event,
    )

    # The financial summary changed, so the old Redis cache must be removed.
    delete_cache(f"summary:{deleted_event['user_id']}")

    return {
        "message": "Transaction deleted successfully",
        "transaction_id": transaction_id,
    }
