from typing import Optional

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    # Optional id is used for idempotency when another service creates a transaction from a confirmed goal operation.
    id: Optional[str] = None
    user_id: str
    amount: float = Field(gt=0)
    category: str
    type: str
    description: Optional[str] = None
    date: Optional[str] = None


class TransactionResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    category: str
    type: str
    description: Optional[str] = None
    date: Optional[str] = None

    class Config:
        from_attributes = True


class SummaryResponse(BaseModel):
    user_id: str
    total_income: float
    total_expense: float
    balance: float
    transactions_count: int