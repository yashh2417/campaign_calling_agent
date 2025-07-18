from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
import re
from datetime import datetime

# Request schemas
class TranscriptItem(BaseModel):
    speaker: str
    text: str

class CallPayload(BaseModel):
    call_id: str
    transcript: List[TranscriptItem]
    summary: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None

class SendCallRequest(BaseModel):
    phone_number: str
    pathway_id: str
    variables: Optional[Dict[str, Any]] = None
    task: Optional[str] = None
    record: Optional[bool] = None
    webhook: Optional[str] = None

    @field_validator('phone_number')
    def validate_phone_number(cls, v):
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

class BatchCallRequestItem(BaseModel):
    phone_number: str
    variables: Optional[Dict[str, Any]] = None

class BatchCallRequest(BaseModel):
    pathway_id: str
    calls: List[BatchCallRequestItem]
    task: Optional[str] = None
    record: Optional[bool] = None
    webhook: Optional[str] = None

# Database schemas
class CallBase(BaseModel):
    emotion: Optional[str]
    from_phone: Optional[str]
    to_phone: Optional[str]
    completed: Optional[bool]
    summary: Optional[str]
    call_transcript: Optional[str]

class CallCreate(CallBase):
    call_id: str
    
    # --- NEW: Added batch_id ---
    batch_id: Optional[str] = None
    
    embedding: Optional[list[float]]

class CallRead(CallBase):
    call_id: str
    batch_id: Optional[str] = None
    created_at: Optional[datetime]

    class Config:
        orm_mode = True
