from typing import Optional

from pydantic import BaseModel, Field


class SavingsGoalCreate(BaseModel):
    user_id: str
    title: str = Field(min_length=2, max_length=100)
    target_amount: float = Field(gt=0)


class SavingsGoalUpdate(BaseModel):
    amount: float = Field(gt=0)


class SavingsGoalResponse(BaseModel):
    id: str
    user_id: str
    title: str
    target_amount: float
    current_amount: float
    image_url: Optional[str] = None

    class Config:
        from_attributes = True