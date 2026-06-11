from typing import Optional

from pydantic import BaseModel, Field


class SavingsGoalCreate(BaseModel):
    user_id: str
    title: str = Field(min_length=2, max_length=100)
    target_amount: float = Field(gt=0)


class SavingsGoalUpdate(BaseModel):
    amount: float = Field(gt=0)


class GoalOperationCreate(BaseModel):
    user_id: Optional[str] = None
    operation_type: str = Field(pattern="^(DEPOSIT|WITHDRAW)$")
    amount: float = Field(gt=0)


class SavingsGoalResponse(BaseModel):
    id: str
    user_id: str
    title: str
    target_amount: float
    current_amount: float
    image_url: Optional[str] = None
    status: str = "ACTIVE"

    class Config:
        from_attributes = True


class GoalOperationResponse(BaseModel):
    id: str
    user_id: str
    goal_id: str
    operation_type: str
    amount: float
    status: str
    failure_reason: Optional[str] = None
    created_at: Optional[object] = None
    processed_at: Optional[object] = None

    class Config:
        from_attributes = True
