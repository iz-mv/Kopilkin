from datetime import datetime, timezone
import uuid

from fastapi import FastAPI, HTTPException, Depends, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import User
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.events import publish_event
from app.cache import (
    get_cache,
    set_cache,
    delete_cache,
    blacklist_token,
    is_token_blacklisted,
)
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

from app.storage import upload_image_to_minio, delete_file_from_minio


app = FastAPI(title="Kopilkin Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    jti = payload.get("jti")
    user_id = payload.get("sub")

    if not jti or not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    if is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token has been logged out")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


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
        password_hash=hash_password(data.password),
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


@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "name": user.name,
    }


@app.post("/logout")
def logout(data: LogoutRequest):
    payload = decode_access_token(data.access_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    jti = payload.get("jti")
    exp = payload.get("exp")

    if not jti or not exp:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    now = int(datetime.now(timezone.utc).timestamp())
    ttl_seconds = max(exp - now, 1)

    blacklist_token(jti=jti, ttl_seconds=ttl_seconds)

    return {"message": "Logged out successfully"}


@app.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/me/avatar", response_model=UserResponse)
def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    old_avatar_url = current_user.avatar_url

    avatar_url = upload_image_to_minio(
        file=file,
        folder=f"avatars/{current_user.id}"
    )

    current_user.avatar_url = avatar_url

    db.commit()
    db.refresh(current_user)

    delete_cache(f"user:{current_user.id}")

    if old_avatar_url:
        delete_file_from_minio(old_avatar_url)

    return current_user


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
        "avatar_url": user.avatar_url,
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