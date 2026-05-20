from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid

from app.database import Base, engine, get_db
from app.models import Transaction
from app.schemas import TransactionCreate, TransactionResponse, SummaryResponse


app = FastAPI(title="Kopilkin Transaction Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"service": "transaction-service", "status": "running"}


@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    if data.type not in ["income", "expense"]:
        raise HTTPException(
            status_code=400,
            detail="Transaction type must be either 'income' or 'expense'"
        )

    transaction = Transaction(
        id=str(uuid.uuid4()),
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

    return transaction


@app.get("/transactions/{user_id}", response_model=list[TransactionResponse])
def get_user_transactions(user_id: str, db: Session = Depends(get_db)):
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    return transactions


@app.get("/transactions/{user_id}/summary", response_model=SummaryResponse)
def get_user_summary(user_id: str, db: Session = Depends(get_db)):
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .all()
    )

    total_income = sum(t.amount for t in transactions if t.type == "income")
    total_expense = sum(t.amount for t in transactions if t.type == "expense")
    balance = total_income - total_expense

    return {
        "user_id": user_id,
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": balance,
        "transactions_count": len(transactions),
    }


@app.get("/summary/{user_id}", response_model=SummaryResponse)
def get_user_summary_alias(user_id: str, db: Session = Depends(get_db)):
    return get_user_summary(user_id, db)


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: str, db: Session = Depends(get_db)):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()

    return {
        "message": "Transaction deleted successfully",
        "transaction_id": transaction_id,
    }