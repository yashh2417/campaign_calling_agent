from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP, Integer, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from core.database import Base
from sqlalchemy.dialects.postgresql import UUID

class Call(Base):
    __tablename__ = "calls"
    
    call_id = Column(String(255), primary_key=True, nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey('campaigns.campaign_id', ondelete='CASCADE'), nullable=True, index=True)
    batch_id = Column(String(255), nullable=True, index=True)
    emotion = Column(String(20), nullable=True)
    from_phone = Column(String(50), nullable=True)
    to_phone = Column(String(50), nullable=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.now(), index=True)
    completed = Column(Boolean, nullable=True, default=False)
    summary = Column(Text, nullable=True)
    call_transcript = Column(Text, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    followup_scheduled = Column(Boolean, default=False, nullable=False)
    followup_datetime = Column(TIMESTAMP(timezone=True), nullable=True)
    
    # Additional fields for better tracking
    call_duration = Column(Integer, nullable=True)  # in seconds
    call_status = Column(String(50), nullable=True)  # success, failed, no_answer, busy, etc.
    cost = Column(String(10), nullable=True)  # cost of the call
    
    # Relationships
    campaign = relationship("Campaign", back_populates="calls")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_calls_campaign_created', 'campaign_id', 'created_at'),
        Index('idx_calls_batch_created', 'batch_id', 'created_at'),
        Index('idx_calls_phone_created', 'to_phone', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Call(id={self.call_id}, campaign_id={self.campaign_id}, completed={self.completed})>"