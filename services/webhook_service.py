import uuid
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from core.database import logger
from crud.db_calls import create_call_db
from schemas.call_data_schemas import CallCreate

async def process_webhook(request: Request, db: Session, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")
        call_id = data.get("call_id")
        if not call_id:
            raise HTTPException(status_code=400, detail="Missing call_id")
        
        metadata = data.get('metadata', {})
        batch_id = metadata.get('batch_id')
        campaign_id_str = metadata.get('campaign_id')
        campaign_id = uuid.UUID(campaign_id_str) if campaign_id_str else None

        # You can add more processing logic here (e.g., emotion, analysis)
        
        call_to_create = CallCreate(
            call_id=call_id,
            campaign_id=campaign_id,
            batch_id=batch_id,
            to_phone=data.get("to"),
            from_phone=data.get("from"),
            summary=data.get("summary"),
            call_transcript=data.get("concatenated_transcript", "").strip(),
            completed=data.get("completed"),
        )
        create_call_db(db=db, call=call_to_create)

        return {"status": "success", "message": "Call processed", "call_id": call_id}

    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")