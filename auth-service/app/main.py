from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Dict
from fastapi.middleware.cors import CORSMiddleware
import uuid

app = FastAPI(title="Kopilkin Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

users_db: Dict[str, dict] = {}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str


@app.get("/")
def root():
    return {"service": "auth-service", "status": "running"}


@app.post("/register", response_model=UserResponse)
def register(data: RegisterRequest):
    for user in users_db.values():
        if user["email"] == data.email:
            raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    users_db[user_id] = {
        "id": user_id,
        "email": data.email,
        "password": data.password,
        "name": data.name,
    }

    return {
        "id": user_id,
        "email": data.email,
        "name": data.name,
    }


@app.post("/login")
def login(data: LoginRequest):
    for user in users_db.values():
        if user["email"] == data.email and user["password"] == data.password:
            return {
                "message": "Login successful",
                "access_token": f"fake-token-{user['id']}",
                "user_id": user["id"],
                "name": user["name"],
            }

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str):
    user = users_db.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
    }


@app.get("/google/login")
def google_login_placeholder():
    return {
        "message": "Google OAuth will be added in the next step",
        "status": "placeholder"
    }