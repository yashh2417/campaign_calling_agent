from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: str
    phone_number: str
    password: str
    business_name: Optional[str] = None
    business_details: Optional[str] = None

class UserRead(BaseModel):
    id: int
    name: str
    email: str
    phone_number: str
    business_name: Optional[str] = None
    business_details: Optional[str] = None

    class Config:
        from_attributes = True