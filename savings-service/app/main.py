from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid

from app.database import Base, engine, get_db
from app.models import SavingsGoal, GoalOperation
from app.schemas import (
    SavingsGoalCreate,
    SavingsGoalUpdate,
    SavingsGoalResponse,
    GoalOperationCreate,
    GoalOperationResponse,
)
from app.events import publish_event
from app.storage import (
    upload_image_to_minio,
    delete_file_from_minio,
    cleanup_goal_images_except_current,
)
from app.grpc_server import start_grpc_server, stop_grpc_server


app = FastAPI(title="Kopilkin Savings Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def on_startup():
    start_grpc_server()


@app.on_event("shutdown")
def on_shutdown():
    stop_grpc_server()



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
        status="ACTIVE",
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
            "status": goal.status,
        },
    )

    return goal


@app.get("/goals/{user_id}", response_model=list[SavingsGoalResponse])
def get_user_goals(user_id: str, db: Session = Depends(get_db)):
    goals = (
        db.query(SavingsGoal)
        .filter(SavingsGoal.user_id == user_id)
        .filter(SavingsGoal.status != "DELETED")
        .order_by(SavingsGoal.created_at.desc())
        .all()
    )

    return goals


@app.post("/goals/{goal_id}/operations", response_model=GoalOperationResponse)
def create_goal_operation(
    goal_id: str,
    data: GoalOperationCreate,
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    if not goal or goal.status == "DELETED":
        raise HTTPException(status_code=404, detail="Savings goal not found")

    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    operation_type = data.operation_type.upper()

    if operation_type not in ["DEPOSIT", "WITHDRAW"]:
        raise HTTPException(
            status_code=400,
            detail="Operation type must be either DEPOSIT or WITHDRAW",
        )

    # If user_id is not sent from frontend, use goal owner
    # This keeps old frontend calls simple and still stores the correct user
    operation_user_id = data.user_id or goal.user_id

    if operation_user_id != goal.user_id:
        raise HTTPException(
            status_code=403,
            detail="Operation user does not match goal owner",
        )

    operation = GoalOperation(
        id=str(uuid.uuid4()),
        user_id=operation_user_id,
        goal_id=goal.id,
        operation_type=operation_type,
        amount=data.amount,
        status="PENDING",
        failure_reason=None,
    )

    db.add(operation)
    db.commit()
    db.refresh(operation)

    publish_event(
        topic="goal.operation.created",
        key=operation.user_id,
        event={
            "event_type": "goal.operation.created",
            "operation_id": operation.id,
            "goal_id": goal.id,
            "goal_title": goal.title,
            "user_id": operation.user_id,
            "operation_type": operation.operation_type,
            "amount": operation.amount,
            "status": operation.status,
        },
    )

    return operation


@app.patch("/goals/{goal_id}/add", response_model=GoalOperationResponse)
def add_money_to_goal(
    goal_id: str,
    data: SavingsGoalUpdate,
    db: Session = Depends(get_db),
):
    return create_goal_operation(
        goal_id=goal_id,
        data=GoalOperationCreate(operation_type="DEPOSIT", amount=data.amount),
        db=db,
    )


@app.patch("/goals/{goal_id}/withdraw", response_model=GoalOperationResponse)
def withdraw_money_from_goal(
    goal_id: str,
    data: SavingsGoalUpdate,
    db: Session = Depends(get_db),
):
    return create_goal_operation(
        goal_id=goal_id,
        data=GoalOperationCreate(operation_type="WITHDRAW", amount=data.amount),
        db=db,
    )


@app.get("/goals/{goal_id}/operations", response_model=list[GoalOperationResponse])
def get_goal_operations(goal_id: str, db: Session = Depends(get_db)):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    if not goal:
        raise HTTPException(status_code=404, detail="Savings goal not found")

    operations = (
        db.query(GoalOperation)
        .filter(GoalOperation.goal_id == goal_id)
        .order_by(GoalOperation.created_at.desc())
        .limit(20)
        .all()
    )

    return operations


@app.post("/goals/{goal_id}/image", response_model=SavingsGoalResponse)
def upload_goal_image(
    goal_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()

    if not goal or goal.status == "DELETED":
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

    goal.status = "DELETED"

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
