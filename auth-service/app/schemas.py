from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    name: str = Field(min_length=2, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str
    user_id: str
    name: str


class LogoutRequest(BaseModel):
    access_token: str