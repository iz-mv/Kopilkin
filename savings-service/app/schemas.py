from pydantic import BaseModel


class SavingsGoalCreate(BaseModel):
    user_id: str
    title: str
    target_amount: float


class SavingsGoalUpdate(BaseModel):
    amount: float


class SavingsGoalResponse(BaseModel):
    id: str
    user_id: str
    title: str
    target_amount: float
    current_amount: float

    class Config:
        from_attributes = True