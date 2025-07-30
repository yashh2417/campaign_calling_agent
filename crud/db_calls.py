from sqlalchemy.orm import Session
from models.call_table import Call
from schemas.call_data_schemas import CallCreate

def get_calls_from_db(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Call).offset(skip).limit(limit).all()

def get_call_by_id(db: Session, call_id: str):
    return db.query(Call).filter(Call.call_id == call_id).first()

def create_call_db(db: Session, call: CallCreate):
    db_call = Call(**call.model_dump())
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    return db_call