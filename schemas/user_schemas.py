# Enhanced schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import re

class UserBase(BaseModel):
    name: str
    email: str
    phone_number: str
    business_name: Optional[str] = None
    business_details: Optional[str] = None

    @field_validator('email')
    def validate_email(cls, v):
        if not v or '@' not in v:
            raise ValueError('Valid email address is required')
        return v.lower()

    @field_validator('phone_number')
    def validate_phone(cls, v):
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format. Use international format like +1234567890')
        return v

    @field_validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()

class UserCreate(UserBase):
    password: str

    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    business_name: Optional[str] = None
    business_details: Optional[str] = None
    password: Optional[str] = None

    @field_validator('email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('Valid email address is required')
        return v.lower() if v else v

    @field_validator('phone_number')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @field_validator('password')
    def validate_password(cls, v):
        if v and len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserRead(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str