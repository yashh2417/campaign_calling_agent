from fastapi import APIRouter, Depends, BackgroundTasks, Request, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from schemas.call_data_schemas import BatchCallRequest, CallRead
from services.call_creation_service import start_campaign_calls
from services.webhook_service import process_webhook
from crud.db_calls import get_calls_from_db, get_call_by_id
from core.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/start_campaign")
async def run_campaign(request: BatchCallRequest, db: Session = Depends(get_db)):
    """Start a campaign and initiate calls"""
    try:
        return await start_campaign_calls(request, db)
    except Exception as e:
        logger.error(f"Error starting campaign: {e}")
        raise

@router.post("/webhook")
async def webhook_receiver(
    request: Request, 
    db: Session = Depends(get_db), 
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Receive webhooks from Bland AI"""
    try:
        return await process_webhook(request, db, background_tasks)
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise

@router.get("/api/calls", response_model=List[CallRead], tags=["Calls"])
def get_calls_history(
    skip: int = 0, 
    limit: int = 100, 
    campaign_id: Optional[str] = None,
    completed: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get call history with optional filtering"""
    # try:
    #     if limit > 1000:
    #         limit = 1000
        
    #     calls = get_calls_from_db

    try:
        calls = get_calls_from_db(db, skip=skip, limit=limit)
        return calls
    except Exception as e:
        logger.error(f"Error fetching calls from database: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve call records.")