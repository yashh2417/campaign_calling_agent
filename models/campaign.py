import uuid
import enum
from sqlalchemy import Column, String, Integer, TIMESTAMP, Text, func, JSON, Enum as SQLAlchemyEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base

class CampaignStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    campaign_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)
    batch_id = Column(String, nullable=True, index=True)
    campaign_group_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    campaign_name = Column(String, nullable=False)
    agent_name = Column(String, nullable=True)
    status = Column(SQLAlchemyEnum(CampaignStatus), default=CampaignStatus.draft, nullable=False, index=True)
    task = Column(Text, nullable=True)
    voice = Column(String, nullable=True)
    pathway_id = Column(String, nullable=True)
    start_date = Column(TIMESTAMP(timezone=True), nullable=True)
    end_date = Column(TIMESTAMP(timezone=True), nullable=True)
    contact_list = Column(JSON, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())
    
    # Relationships
    calls = relationship("Call", back_populates="campaign", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Campaign(id={self.campaign_id}, name='{self.campaign_name}', status='{self.status}')>"