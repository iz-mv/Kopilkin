from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
from datetime import datetime

app = FastAPI(title="Kopilkin Transaction Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

transactions_db: Dict[str, dict] = {}


class TransactionCreate(BaseModel):
    user_id: str
    amount: float
    category: str
    date: str
    type: str  # expense or income
    description: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    category: str
    date: str
    type: str
    description: Optional[str] = None
    created_at: str


@app.get("/")
def root():
    return {"service": "transaction-service", "status": "running"}


@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(data: TransactionCreate):
    if data.type not in ["expense", "income"]:
        raise HTTPException(status_code=400, detail="type must be 'expense' or 'income'")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    transaction_id = str(uuid.uuid4())
    transaction = {
        "id": transaction_id,
        "user_id": data.user_id,
        "amount": data.amount,
        "category": data.category,
        "date": data.date,
        "type": data.type,
        "description": data.description,
        "created_at": datetime.utcnow().isoformat(),
    }
    transactions_db[transaction_id] = transaction
    return transaction


@app.get("/transactions/{user_id}", response_model=List[TransactionResponse])
def get_user_transactions(user_id: str):
    user_transactions = [t for t in transactions_db.values() if t["user_id"] == user_id]
    user_transactions.sort(key=lambda t: (t["date"], t["created_at"]), reverse=True)
    return user_transactions


@app.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: str):
    transaction = transactions_db.get(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    del transactions_db[transaction_id]
    return {"message": "Transaction deleted successfully"}


@app.get("/transactions/{user_id}/summary")
def get_summary(user_id: str):
    user_transactions = [t for t in transactions_db.values() if t["user_id"] == user_id]

    total_expense = sum(t["amount"] for t in user_transactions if t["type"] == "expense")
    total_income = sum(t["amount"] for t in user_transactions if t["type"] == "income")

    by_category = {}
    for t in user_transactions:
        by_category[t["category"]] = by_category.get(t["category"], 0) + t["amount"]

    return {
        "user_id": user_id,
        "total_expense": total_expense,
        "total_income": total_income,
        "by_category": by_category,
    }