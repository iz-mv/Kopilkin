from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid

from app.database import Base, engine, get_db
from app.models import SavingsGoal
from app.schemas import SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalResponse
from app.events import publish_event
from app.storage import (
    upload_image_to_minio,
    delete_file_from_minio,
    cleanup_goal_images_except_current,
)


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
        image_url=None,
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
            "image_url": goal.image_url,
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
    db: Session = Depends(get_db),
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
            "image_url": goal.image_url,
        },
    )

    return goal


@app.post("/goals/{goal_id}/image", response_model=SavingsGoalResponse)
def upload_goal_image(
    goal_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    old_image_url = goal.image_url

    image_url = upload_image_to_minio(
        file=file,
        folder=f"goals/{goal.id}",
    )

    goal.image_url = image_url

    db.commit()
    db.refresh(goal)

    if old_image_url:
        delete_file_from_minio(old_image_url)

    cleanup_goal_images_except_current(
        goal_id=goal.id,
        current_image_url=goal.image_url,
    )

    publish_event(
        topic="goal.image.updated",
        key=goal.user_id,
        event={
            "event_type": "goal.image.updated",
            "goal_id": goal.id,
            "user_id": goal.user_id,
            "image_url": goal.image_url,
        },
    )

    return goal


@app.delete("/goals/{goal_id}")
def delete_goal(goal_id: str, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    old_image_url = goal.image_url
    user_id = goal.user_id

    db.delete(goal)
    db.commit()

    if old_image_url:
        delete_file_from_minio(old_image_url)

    cleanup_goal_images_except_current(
        goal_id=goal_id,
        current_image_url=None,
    )

    publish_event(
        topic="goal.deleted",
        key=user_id,
        event={
            "event_type": "goal.deleted",
            "goal_id": goal_id,
            "user_id": user_id,
        },
    )

    return {
        "message": "Savings goal deleted successfully",
        "goal_id": goal_id,
    }
