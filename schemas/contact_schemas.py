from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ContactBase(BaseModel):
    name: str
    phone_number: str
    company_name: Optional[str] = None
    email: Optional[str] = None
    tags: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(ContactBase):
    pass

class ContactRead(ContactBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContactBatchCreate(BaseModel):
    contacts: List[ContactCreate]