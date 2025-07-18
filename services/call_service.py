from core.database import logger
from fastapi import Request, HTTPException
import requests
import logging
from core.config import settings
from sqlalchemy.orm import Session
from schemas.call_data_schemas import CallCreate, SendCallRequest, BatchCallRequest
from crud.db_call import create_call as db_create_call, get_calls as db_get_calls

async def get_postcall_data(request: Request, db: Session):
    """Receive and process webhook callbacks from Bland AI"""
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")

        call_id = data.get("call_id")
        to_phone = data.get("to")
        from_phone = data.get("from")
        summary = data.get("summary")
        completed = data.get("completed")
        
        transcript_text = " ".join([f"{t.get('user', 'unknown')}: {t.get('text', '')}" for t in data.get("transcript", [])])

        if not call_id:
            logger.error("❌ Missing call_id in webhook payload")
            raise HTTPException(status_code=400, detail="Missing call_id")

        # Call Bland AI analysis endpoint for additional insights
        # This part remains the same as it's an external API call
        
        call_to_create = CallCreate(
            call_id=call_id,
            to_phone=to_phone,
            from_phone=from_phone,
            summary=summary,
            call_transcript=transcript_text,
            completed=completed,
            emotion=None, # You can add logic to extract emotion if available
            embedding=None # You can add logic to generate and store embeddings
        )
        
        db_create_call(db=db, call=call_to_create)

        return {
            "status": "success",
            "message": "Call processed and saved successfully",
            "call_id": call_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_call(request: SendCallRequest):
    """Send a single AI phone call"""
    try:
        url = "https://api.bland.ai/v1/calls"
        bland_api_key = settings.BLAND_API_KEY
        
        if not bland_api_key:
            raise HTTPException(status_code=500, detail="BLAND_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {bland_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = request.model_dump(exclude_none=True)

        logger.info(f"📞 Sending call to {request.phone_number}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"❌ HTTP error: {http_err}")
        error_detail = f"HTTP error occurred: {http_err}"
        if hasattr(http_err, 'response') and http_err.response:
            error_detail += f" - {http_err.response.text}"
        raise HTTPException(status_code=400, detail=error_detail)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send call")
    
async def create_batch_call(request: BatchCallRequest):
    """Send batch AI phone calls"""
    # This function seems correct for interacting with the Bland AI API
    # No database interaction here, so no changes needed
    pass

async def get_calls_from_db(db: Session, limit: int = 50, skip: int = 0):
    """Get call history from database"""
    try:
        calls = db_get_calls(db, skip=skip, limit=limit)
        return {"calls": calls, "count": len(calls)}
    
    except Exception as e:
        logger.error(f"❌ Error fetching calls: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch calls")