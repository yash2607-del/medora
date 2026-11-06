from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    age: int = Field(..., ge=1, le=120)
    gender: str = Field(..., min_length=1, max_length=30)
    city: str = Field(..., min_length=1, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field("India", max_length=100)
    email: Optional[EmailStr] = None
    username: str = Field(..., min_length=4, max_length=100)
    password: str = Field(..., min_length=8, max_length=72)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=72)


class LoginResponse(BaseModel):
    authenticated: bool
    username: str
    patient_id: str


class AuthMeResponse(BaseModel):
    authenticated: bool
    username: Optional[str] = None
    patient_id: Optional[str] = None


class LogoutResponse(BaseModel):
    authenticated: bool
    message: str