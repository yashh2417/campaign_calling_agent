from sqlalchemy.orm import Session
from models.call_table import Call
from schemas.call_data_schemas import CallCreate

def create_call(db: Session, call: CallCreate):
    db_call = Call(**call.model_dump())
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    return db_call

def get_call(db: Session, call_id: str):
    return db.query(Call).filter(Call.call_id == call_id).first()

def get_calls(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Call).offset(skip).limit(limit).all()