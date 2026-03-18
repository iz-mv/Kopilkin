from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import uuid

app = FastAPI(title="Kopilkin Savings Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

goals_db: Dict[str, dict] = {}


class GoalCreate(BaseModel):
    user_id: str
    title: str
    target_amount: float


class GoalUpdate(BaseModel):
    amount_change: float


class GoalResponse(BaseModel):
    id: str
    user_id: str
    title: str
    target_amount: float
    current_amount: float
    progress_percent: float


@app.get("/")
def root():
    return {"service": "savings-service", "status": "running"}


@app.post("/goals", response_model=GoalResponse)
def create_goal(data: GoalCreate):
    if data.target_amount <= 0:
        raise HTTPException(status_code=400, detail="Target amount must be greater than 0")

    goal_id = str(uuid.uuid4())
    goal = {
        "id": goal_id,
        "user_id": data.user_id,
        "title": data.title,
        "target_amount": data.target_amount,
        "current_amount": 0.0,
    }
    goals_db[goal_id] = goal

    return {
        **goal,
        "progress_percent": 0.0,
    }


@app.get("/goals/{user_id}", response_model=List[GoalResponse])
def get_user_goals(user_id: str):
    user_goals = [g for g in goals_db.values() if g["user_id"] == user_id]

    result = []
    for goal in user_goals:
        progress = 0.0
        if goal["target_amount"] > 0:
            progress = round((goal["current_amount"] / goal["target_amount"]) * 100, 2)

        result.append({
            **goal,
            "progress_percent": progress
        })

    return result


@app.patch("/goals/{goal_id}/add", response_model=GoalResponse)
def update_goal_amount(goal_id: str, data: GoalUpdate):
    goal = goals_db.get(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if data.amount_change == 0:
        raise HTTPException(status_code=400, detail="Amount change cannot be 0")

    new_amount = goal["current_amount"] + data.amount_change

    if new_amount < 0:
        raise HTTPException(status_code=400, detail="Current amount cannot go below 0")

    goal["current_amount"] = new_amount

    progress = 0.0
    if goal["target_amount"] > 0:
        progress = round((goal["current_amount"] / goal["target_amount"]) * 100, 2)

    return {
        **goal,
        "progress_percent": progress
    }