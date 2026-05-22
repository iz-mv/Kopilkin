from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid

from app.database import Base, engine, get_db
from app.models import User
from app.schemas import RegisterRequest, LoginRequest, UserResponse, UserUpdateRequest
from app.events import publish_event
from app.cache import get_cache, set_cache, delete_cache


app = FastAPI(title="Kopilkin Auth Service")

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
    return {"service": "auth-service", "status": "running"}


@app.post("/register", response_model=UserResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == data.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        password=data.password,
        name=data.name,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    publish_event(
        topic="user.registered",
        key=user.id,
        event={
            "event_type": "user.registered",
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
        },
    )

    return user


@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.password == data.password:
        return {
            "message": "Login successful",
            "access_token": f"fake-token-{user.id}",
            "user_id": user.id,
            "name": user.name,
        }

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db)):
    cache_key = f"user:{user_id}"

    cached_user = get_cache(cache_key)
    if cached_user:
        return cached_user

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
    }

    set_cache(cache_key, user_data, ttl_seconds=300)

    return user_data


@app.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: str, data: UserUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.name = data.name

    db.commit()
    db.refresh(user)

    delete_cache(f"user:{user_id}")

    return user


@app.get("/google/login")
def google_login_placeholder():
    return {
        "message": "Google OAuth will be added in the next step",
        "status": "placeholder"
    }