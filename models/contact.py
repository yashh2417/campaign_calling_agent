from sqlalchemy import Column, String, Integer, TIMESTAMP, func
from core.database import Base

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False, unique=True, index=True)
    company_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())