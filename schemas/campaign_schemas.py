import uuid
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .contact_schemas import ContactRead
from models.campaign import CampaignStatus
from .contact_schemas import ContactRead

class CampaignBase(BaseModel):
    campaign_name: str
    agent_name: Optional[str] = None
    task: Optional[str] = None
    voice: Optional[str] = None
    pathway_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    contact_list: Optional[List[int]] = []

class CampaignCreate(CampaignBase):
    pass

class CampaignUpdate(CampaignBase):
    status: Optional[str] = None

class CampaignRead(CampaignBase):
    id: int
    campaign_id: uuid.UUID
    
    # --- ADD THIS LINE ---
    batch_id: Optional[str] = None
    # --- END OF ADDITION ---

    campaign_group_id: uuid.UUID
    version: int
    status: str
    created_at: datetime
    history: Optional[List['CampaignRead']] = None
    
    class Config:
        from_attributes = True

CampaignRead.model_rebuild()

class CampaignStatusUpdate(BaseModel):
    status: CampaignStatus