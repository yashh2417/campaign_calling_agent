from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import SessionLocal
from schemas.call_data_schemas import SendCallRequest, BatchCallRequest
from services.call_service import (
    get_postcall_data,
    create_call,
    create_batch_call,
    get_calls_from_db
)

router = APIRouter()

def get_db():
    """Dependency to get a DB session for each request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# The webhook endpoint now correctly accepts and passes 
@router.post("/bland/postcall")
async def receive_postcall(
    request: Request, 
    background_tasks: BackgroundTasks, # FastAPI will automatically provide this
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint to receive data from Bland AI after a call is completed.
    It now correctly supports scheduling background tasks for follow-ups.
    """
    # The 'background_tasks' object is now correctly passed to the service layer.
    return await get_postcall_data(request, db, background_tasks)


@router.post("/bland/sendcall")
async def send_call(request: SendCallRequest):
    """Endpoint to send a single call."""
    return await create_call(request)

@router.post("/bland/sendbatch")
async def send_batch(request: BatchCallRequest):
    """Endpoint to send a batch of calls."""
    return await create_batch_call(request)

@router.get("/calls")
async def get_calls(limit: int = 50, skip: int = 0, db: Session = Depends(get_db)):
    """Endpoint to retrieve call history from the database."""
    return await get_calls_from_db(db, limit, skip)
