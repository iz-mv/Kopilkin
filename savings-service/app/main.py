from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid

from app.database import Base, engine, get_db
from app.models import SavingsGoal
from app.schemas import SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalResponse
from app.events import publish_event


app = FastAPI(title="Kopilkin Savings Service")

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
    return {"service": "savings-service", "status": "running"}


@app.post("/goals", response_model=SavingsGoalResponse)
def create_goal(data: SavingsGoalCreate, db: Session = Depends(get_db)):
    goal = SavingsGoal(
        id=str(uuid.uuid4()),
        user_id=data.user_id,
        title=data.title,
        target_amount=data.target_amount,
        current_amount=0.0,
    )

    db.add(goal)
    db.commit()
    db.refresh(goal)

    publish_event(
        topic="goal.created",
        key=goal.user_id,
        event={
            "event_type": "goal.created",
            "goal_id": goal.id,
            "user_id": goal.user_id,
            "title": goal.title,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
        },
    )

    return goal


@app.get("/goals/{user_id}", response_model=list[SavingsGoalResponse])
def get_user_goals(user_id: str, db: Session = Depends(get_db)):
    goals = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.user_id == user_id)
        .order_by(SavingsGoal.created_at.desc())
        .all()
    )

    return goals


@app.patch("/goals/{goal_id}/add", response_model=SavingsGoalResponse)
def add_money_to_goal(
    goal_id: str,
    data: SavingsGoalUpdate,
    db: Session = Depends(get_db)
):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    goal.current_amount += data.amount

    db.commit()
    db.refresh(goal)

    publish_event(
        topic="goal.updated",
        key=goal.user_id,
        event={
            "event_type": "goal.updated",
            "goal_id": goal.id,
            "user_id": goal.user_id,
            "title": goal.title,
            "amount_change": data.amount,
            "target_amount": goal.target_amount,
            "current_amount": goal.current_amount,
        },
    )

    return goal


@app.delete("/goals/{goal_id}")
def delete_goal(goal_id: str, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    db.delete(goal)
    db.commit()

    return {
        "message": "Savings goal deleted successfully",
        "goal_id": goal_id,
    }