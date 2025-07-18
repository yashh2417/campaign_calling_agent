from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from core.database import SessionLocal
from schemas.call_data_schemas import SendCallRequest, BatchCallRequest
from services.call_service import (
    get_postcall_data,
    create_call,
    create_batch_call,
    get_calls_from_db
)
# We don't need these here anymore for the homepage
# from fastapi.responses import HTMLResponse
# from core.templates import templates

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/bland/postcall")
async def receive_postcall(request: Request, db: Session = Depends(get_db)):
    return await get_postcall_data(request, db)

@router.post("/bland/sendcall")
async def send_call(request: SendCallRequest):
    return await create_call(request)

@router.post("/bland/sendbatch")
async def send_batch(request: BatchCallRequest):
    return await create_batch_call(request)

@router.get("/calls")
async def get_calls(limit: int = 50, skip: int = 0, db: Session = Depends(get_db)):
    return await get_calls_from_db(db, limit, skip)