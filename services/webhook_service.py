import uuid
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import logger
from crud.db_calls import create_call_db
from schemas.call_data_schemas import CallCreate

async def process_webhook(request: Request, db: Session, background_tasks: BackgroundTasks):
    """
    Process incoming webhooks from Bland AI.
    This handles both individual call webhooks and batch status updates.
    """
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")
        
        # Check if this is a batch status webhook or individual call webhook
        if "batch_id" in data and "status" in data and "call_id" not in data:
            # This is a batch status update
            return await handle_batch_status_webhook(data, db)
        else:
            # This is an individual call webhook
            return await handle_call_webhook(data, db, background_tasks)
            
    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def handle_call_webhook(data: dict, db: Session, background_tasks: BackgroundTasks):
    """Handle individual call completion webhooks"""
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
    
    # Extract call details
    call_data = {
        "call_id": call_id,
        "campaign_id": campaign_id,
        "batch_id": batch_id,
        "to_phone": data.get("to") or data.get("phone_number"),
        "from_phone": data.get("from"),
        "summary": data.get("summary"),
        "call_transcript": data.get("concatenated_transcript", "").strip() or data.get("transcript", "").strip(),
        "completed": data.get("completed", data.get("status") == "completed"),
        "emotion": data.get("emotion"),
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

async def handle_batch_status_webhook(data: dict, db: Session):
    """Handle batch status update webhooks"""
    batch_id = data.get("batch_id")
    status = data.get("status")
    
    logger.info(f"📊 Batch status update - Batch ID: {batch_id}, Status: {status}")
    
    # You might want to update campaign status based on batch status
    if status == "completed":
        # Update all campaigns with this batch_id to completed status
        from crud.db_campaign import update_campaign_status
        from sqlalchemy import text
        
        # This is a more complex query - you might want to add a method to db_campaign
        result = db.execute(
            text("UPDATE campaigns SET status = 'completed' WHERE batch_id = :batch_id"),
            {"batch_id": batch_id}
        )
        db.commit()
        
        logger.info(f"✅ Updated campaigns with batch_id {batch_id} to completed status")
    
    return {
        "status": "success",
        "message": f"Batch status updated to {status}",
        "batch_id": batch_id
    }