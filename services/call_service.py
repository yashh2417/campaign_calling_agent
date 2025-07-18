import time
import requests
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import uuid

from core.config import settings
from core.database import logger
from crud.db_call import create_call as db_create_call, get_calls as db_get_calls
from schemas.call_data_schemas import CallCreate, SendCallRequest, BatchCallRequest
from services.embedding_service import generate_embedding

# --- Follow-up Call Logic ---

async def schedule_follow_up_call(phone_number: str, pathway_id: str, original_call_id: str):
    """
    Waits for a specified duration and then places a follow-up call.
    This function is designed to be run in the background.
    """
    follow_up_delay_seconds = 300  # 5 minutes for testing
    logger.info(f"⏰ Scheduling follow-up call to {phone_number} in {follow_up_delay_seconds / 60} minutes for original call {original_call_id}.")
    
    time.sleep(follow_up_delay_seconds)
    
    logger.info(f"📞 Placing scheduled follow-up call to {phone_number}.")
    
    follow_up_request = SendCallRequest(
        phone_number=phone_number,
        pathway_id=pathway_id,
        task=f"Follow-up call for original call ID: {original_call_id}. The previous conversation had a neutral sentiment.",
        webhook=f"{settings.ALLOWED_ORIGINS[0]}/bland/postcall" if settings.ALLOWED_ORIGINS else None
    )
    
    try:
        await create_call(follow_up_request)
    except Exception as e:
        logger.error(f"❌ Failed to place follow-up call to {phone_number}: {e}")


# --- Main Service Functions ---

async def get_postcall_data(request: Request, db: Session, background_tasks: BackgroundTasks):
    """
    Receive and process webhook callbacks from Bland AI.
    This function now enriches the data and triggers follow-ups.
    """
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")

        call_id = data.get("call_id")
        if not call_id:
            raise HTTPException(status_code=400, detail="Missing call_id")

        transcript_text = data.get("concatenated_transcript")

        emotion = "unknown"
        if settings.BLAND_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}"}
                analysis_url = f"https://api.bland.ai/v1/calls/{call_id}/analyze"
                analysis_payload = {
                    "goal": "Determine the customer's sentiment based on the conversation.",
                    "questions": [
                        ["What was the overall sentiment of the person who was called?", "Answer with only one word: positive, neutral, or negative."]
                    ]
                }
                analysis_response = requests.post(analysis_url, json=analysis_payload, headers=headers, timeout=30)
                if analysis_response.status_code == 200:
                    analysis_data = analysis_response.json()
                    logger.info(f"📊 Analysis successful: {analysis_data}")
                    emotion = analysis_data.get('answers', ['unknown'])[0].lower().strip()
                else:
                    logger.error(f"❌ Analysis API error: {analysis_response.status_code} - {analysis_response.text}")
            except Exception as e:
                logger.error(f"❌ Analysis request failed: {e}")

        embedding_vector = generate_embedding(transcript_text)
        
        # --- FIX: Extract batch_id from variables if present ---
        variables = data.get('variables', {})
        batch_id = variables.get('_batch_id')

        call_to_create = CallCreate(
            call_id=call_id,
            batch_id=batch_id,
            to_phone=data.get("to"),
            from_phone=data.get("from"),
            summary=data.get("summary"),
            call_transcript=transcript_text,
            completed=data.get("completed"),
            emotion=emotion,
            embedding=embedding_vector
        )
        db_create_call(db=db, call=call_to_create)

        # --- FIX: Correctly extract pathway_id for follow-up ---
        if emotion == "neutral":
            # The pathway_id is now retrieved from the 'variables' passed through the call
            pathway_id = variables.get('_pathway_id')
            phone_number = data.get("to")
            
            if pathway_id and phone_number:
                background_tasks.add_task(schedule_follow_up_call, phone_number, pathway_id, call_id)
            else:
                logger.warning(f"⚠️ Cannot schedule follow-up for call {call_id}: missing _pathway_id in webhook variables or 'to' phone number.")

        return {"status": "success", "message": "Call processed", "call_id": call_id}

    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def create_call(request: SendCallRequest, batch_id: str = None):
    """Send a single AI phone call. Now includes pathway_id in variables."""
    try:
        url = "https://api.bland.ai/v1/calls"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}", "Content-Type": "application/json"}
        
        payload = request.model_dump(exclude_none=True)
        
        # --- FIX: Inject pathway_id and batch_id into variables ---
        # This ensures they are returned in the webhook payload.
        if 'variables' not in payload or payload['variables'] is None:
            payload['variables'] = {}
        payload['variables']['_pathway_id'] = request.pathway_id
        if batch_id:
            payload['variables']['_batch_id'] = batch_id
        # --- End of Fix ---
            
        payload['analysis_schema'] = {"transcript": "string", "summary": "string"}
        
        logger.info(f"📞 Sending call to {request.phone_number} with payload: {payload}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"❌ HTTP error: {http_err} - {http_err.response.text}")
        raise HTTPException(status_code=400, detail=f"HTTP error from Bland AI: {http_err.response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send call")

async def create_batch_call(request: BatchCallRequest):
    """Send batch AI phone calls by iterating and sending them individually."""
    batch_id = f"batch_{uuid.uuid4()}"
    logger.info(f"📤 Starting batch call job {batch_id} for {len(request.calls)} numbers.")
    responses = []
    for call_item in request.calls:
        try:
            single_call_request = SendCallRequest(
                phone_number=call_item.phone_number,
                pathway_id=request.pathway_id,
                variables=call_item.variables,
                task=request.task,
                record=request.record,
                webhook=request.webhook
            )
            # Pass the generated batch_id to the create_call function
            response = await create_call(single_call_request, batch_id=batch_id)
            responses.append({"status": "success", "data": response})
        except Exception as e:
            logger.error(f"❌ Failed to send call to {call_item.phone_number} in batch {batch_id}: {e}")
            responses.append({"status": "error", "phone_number": call_item.phone_number, "detail": str(e)})
            
    return {"status": "Batch job started", "batch_id": batch_id, "results": responses}

async def get_calls_from_db(db: Session, limit: int = 50, skip: int = 0):
    """Get call history from the database."""
    try:
        return db_get_calls(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"❌ Error fetching calls from DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch calls")
