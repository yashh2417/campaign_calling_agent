from sqlalchemy import Column, String, Boolean, Text, TIMESTAMP
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from core.database import Base

class Call(Base):
    __tablename__ = "calls"
    __table_args__ = {"schema": "public"}

    call_id = Column(String(255), primary_key=True, nullable=False)
    batch_id = Column(String(255), nullable=True, index=True)
    emotion = Column(String(20), nullable=True)
    from_phone = Column(String(50), nullable=True)
    to_phone = Column(String(50), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=True, server_default=func.now())
    completed = Column(Boolean, nullable=True)
    summary = Column(Text, nullable=True)
    call_transcript = Column(Text, nullable=True)
    
    # --- UPDATED: Gemini embedding dimension is 768 ---
    embedding = Column(Vector(768), nullable=True)