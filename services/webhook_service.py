import uuid
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from json import JSONDecodeError  # Import the specific error

from core.database import logger
from crud.db_calls import create_call_db
from schemas.call_data_schemas import CallCreate

async def process_webhook(request: Request, db: Session, background_tasks: BackgroundTasks):
    try:
        # --- THIS IS THE FIX ---
        # We try to parse the JSON, but we are prepared for it to fail.
        try:
            data = await request.json()
        except JSONDecodeError:
            # This happens when Bland AI sends an empty request to verify the URL.
            # We log it and return a success response to let them know our webhook is ready.
            logger.warning("📥 Received webhook with empty body. This is likely a verification request.")
            return {"status": "success", "message": "Webhook verified."}
        # --- END OF FIX ---

        logger.info(f"📥 Incoming Webhook Payload: {data}")
        call_id = data.get("call_id")
        if not call_id:
            # Even if the body is not empty, it might be missing the call_id
            raise HTTPException(status_code=400, detail="Missing call_id in webhook payload")
        
        # This metadata might come from the v2 batch webhook
        metadata = data.get('metadata', {})
        batch_id = metadata.get('batch_id')
        
        # Check for the internal campaign ID we set in the batch call
        internal_campaign_id = metadata.get('internal_campaign_id')

        call_to_create = CallCreate(
            call_id=call_id,
            # If batch_id is in the main payload (from v1 call), use it.
            # Otherwise, it might be in the metadata from a v2 call.
            batch_id=data.get('batch_id', batch_id),
            to_phone=data.get("to"),
            from_phone=data.get("from"),
            summary=data.get("summary"),
            call_transcript=data.get("concatenated_transcript", "").strip(),
            completed=data.get("completed"),
        )
        create_call_db(db=db, call=call_to_create)

        return {"status": "success", "message": "Call processed", "call_id": call_id}

    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")