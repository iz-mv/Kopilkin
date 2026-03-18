from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid

app = FastAPI(title="Kopilkin Transaction Service")

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


@app.get("/")
def root():
    return {"service": "transaction-service", "status": "running"}


@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(data: TransactionCreate):
    if data.type not in ["expense", "income"]:
        raise HTTPException(status_code=400, detail="type must be 'expense' or 'income'")

    transaction_id = str(uuid.uuid4())
    transaction = {
        "id": transaction_id,
        "user_id": data.user_id,
        "amount": data.amount,
        "category": data.category,
        "date": data.date,
        "type": data.type,
        "description": data.description,
    }
    transactions_db[transaction_id] = transaction
    return transaction


@app.get("/transactions/{user_id}", response_model=List[TransactionResponse])
def get_user_transactions(user_id: str):
    return [t for t in transactions_db.values() if t["user_id"] == user_id]


@app.get("/transactions/{user_id}/summary")
def get_summary(user_id: str):
    user_transactions = [t for t in transactions_db.values() if t["user_id"] == user_id]

    total_expense = sum(t["amount"] for t in user_transactions if t["type"] == "expense")
    total_income = sum(t["amount"] for t in user_transactions if t["type"] == "income")

    by_category = {}
    for t in user_transactions:
        if t["type"] == "expense":
            by_category[t["category"]] = by_category.get(t["category"], 0) + t["amount"]

    return {
        "user_id": user_id,
        "total_expense": total_expense,
        "total_income": total_income,
        "by_category": by_category,
    }