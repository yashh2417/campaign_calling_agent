# schemas/user_schemas.py
from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: str
    business_name: Optional[str] = None
    business_details: Optional[str] = None

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()

    @validator('phone_number')
    def phone_number_format(cls, v):
        if not v.startswith('+'):
            raise ValueError('Phone number must start with + (international format)')
        if len(v) < 10:
            raise ValueError('Phone number too short')
        return v

class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_length(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    business_name: Optional[str] = None
    business_details: Optional[str] = None
    password: Optional[str] = None

    @validator('name')
    def name_must_not_be_empty(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Name cannot be empty')
        return v.strip() if v else v

    @validator('phone_number')
    def phone_number_format(cls, v):
        if v is not None:
            if not v.startswith('+'):
                raise ValueError('Phone number must start with + (international format)')
            if len(v) < 10:
                raise ValueError('Phone number too short')
        return v

    @validator('password')
    def password_length(cls, v):
        if v is not None and len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRead(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
        # For older versions of Pydantic, use:
        # orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserRead

class TokenData(BaseModel):
    user_id: Optional[int] = None