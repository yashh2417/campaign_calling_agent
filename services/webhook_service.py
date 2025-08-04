import uuid
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import logger
from crud.db_calls import create_call_db
from schemas.call_data_schemas import CallCreate
from services.sentiment_service import get_sentiment_from_transcript

async def process_webhook(request: Request, db: Session, background_tasks: BackgroundTasks):
    """
    Process incoming webhooks from Bland AI.
    This handles both individual call webhooks and batch status updates.
    """
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")
        
        call_id = data.get("call_id")
        if not call_id:
            logger.error("❌ Missing call_id in webhook payload")
            raise HTTPException(status_code=400, detail="Missing call_id")
        
        # Extract metadata (this could come from different places in the payload)
        metadata = data.get('metadata', {})
        
        # Try to get campaign_id from various possible locations
        campaign_id_str = None
        if 'campaign_id' in metadata:
            campaign_id_str = metadata['campaign_id']
        elif 'campaign_id' in data:
            campaign_id_str = data['campaign_id']
        
        campaign_id = None
        if campaign_id_str:
            try:
                campaign_id = uuid.UUID(campaign_id_str)
            except ValueError:
                logger.warning(f"⚠️ Invalid campaign_id format: {campaign_id_str}")
        
        # Extract batch_id
        batch_id = data.get('batch_id') or metadata.get('batch_id')

        call_transcript = data.get("concatenated_transcript", "").strip() or data.get("transcript", "").strip()

        emotion = get_sentiment_from_transcript(call_transcript)
        
        # Extract call details
        call_data = {
            "call_id": call_id,
            "campaign_id": campaign_id,
            "batch_id": batch_id,
            "to_phone": data.get("to") or data.get("phone_number"),
            "from_phone": data.get("from"),
            "summary": data.get("summary"),
            "call_transcript": call_transcript,
            "completed": data.get("completed", data.get("status") == "completed"),
            "emotion": emotion,
        }
        
        # Remove None values
        call_data = {k: v for k, v in call_data.items() if v is not None}
        
        try:
            call_to_create = CallCreate(**call_data)
            created_call = create_call_db(db=db, call=call_to_create)
            
            logger.info(f"✅ Successfully processed call webhook for call_id: {call_id}")
            
            return {
                "status": "success", 
                "message": "Call processed successfully", 
                "call_id": call_id,
                "campaign_id": str(campaign_id) if campaign_id else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error creating call record for {call_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create call record: {str(e)}")
            
    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")