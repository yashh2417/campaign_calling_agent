from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
import re
from datetime import datetime

# --- Request Schemas ---

class SendCallRequest(BaseModel):
    phone_number: str
    pathway_id: str
    variables: Optional[Dict[str, Any]] = None
    task: Optional[str] = None
    record: Optional[bool] = None
    webhook: Optional[str] = None
    
    # metadata field for passthrough data
    metadata: Optional[Dict[str, Any]] = None

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

# --- Database Schemas ---

class CallBase(BaseModel):
    emotion: Optional[str]
    from_phone: Optional[str]
    to_phone: Optional[str]
    completed: Optional[bool]
    summary: Optional[str]
    call_transcript: Optional[str]
    followup_scheduled: Optional[bool] = False
    followup_datetime: Optional[datetime] = None

class CallCreate(CallBase):
    call_id: str
    batch_id: Optional[str] = None
    embedding: Optional[list[float]]

class CallRead(CallBase):
    call_id: str
    batch_id: Optional[str] = None
    created_at: Optional[datetime]

    class Config:
        orm_mode = True
