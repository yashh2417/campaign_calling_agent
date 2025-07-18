import time
import requests
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from core.config import settings
from core.database import logger
from crud.db_call import create_call as db_create_call, get_calls as db_get_calls
from schemas.call_data_schemas import CallCreate, SendCallRequest, BatchCallRequest
# This correctly points to your Gemini embedding service
from services.embedding_service import generate_embedding

# --- Follow-up Call Logic ---

async def schedule_follow_up_call(phone_number: str, pathway_id: str, original_call_id: str):
    """
    Waits for a specified duration and then places a follow-up call.
    This function is designed to be run in the background.
    """
    follow_up_delay_seconds = 300  # 1 hour
    logger.info(f"⏰ Scheduling follow-up call to {phone_number} in {follow_up_delay_seconds / 60} minutes for original call {original_call_id}.")
    
    # In a production environment, a more robust task queue like Celery or ARQ
    # is recommended over time.sleep() for long-running background tasks.
    time.sleep(follow_up_delay_seconds)
    
    logger.info(f"📞 Placing scheduled follow-up call to {phone_number}.")
    
    # Prepare the request for the follow-up call
    follow_up_request = SendCallRequest(
        phone_number=phone_number,
        pathway_id=pathway_id,
        task=f"Follow-up call for original call ID: {original_call_id}. The previous conversation had a neutral sentiment.",
        # Ensure your webhook URL is publicly accessible
        webhook=f"{settings.ALLOWED_ORIGINS[0]}/bland/postcall" if settings.ALLOWED_ORIGINS else None
    )
    
    try:
        # Reuse the existing create_call function to place the new call
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

        # --- Data Enrichment ---
        
        # 1. Process Transcript from the webhook payload
        transcript_text = " ".join([f"{t.get('user', 'unknown')}: {t.get('text', '')}" for t in data.get("transcript", [])])

        # 2. Analyze Emotion via Bland AI
        emotion = "unknown"
        if settings.BLAND_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}"}
                analysis_url = f"https://api.bland.ai/v1/calls/{call_id}/analyze"
                # This payload correctly asks for one of the three desired emotions.
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
                    # This robustly extracts the single-word response.
                    emotion = analysis_data.get('data', [{}])[0].get('response', 'unknown').lower().strip()
                else:
                    logger.error(f"❌ Analysis API error: {analysis_response.status_code} - {analysis_response.text}")
            except Exception as e:
                logger.error(f"❌ Analysis request failed: {e}")

        # 3. Generate Vector Embedding using the configured service (Gemini)
        embedding_vector = generate_embedding(transcript_text)

        # --- Database Interaction ---
        call_to_create = CallCreate(
            call_id=call_id,
            to_phone=data.get("to"),
            from_phone=data.get("from"),
            summary=data.get("summary"),
            call_transcript=transcript_text, 
            completed=data.get("completed"),
            emotion=emotion,
            embedding=embedding_vector
        )
        db_create_call(db=db, call=call_to_create)

        # --- Follow-up Logic ---
        if emotion == "neutral":
            original_call_data = data.get('request_data', {})
            pathway_id = original_call_data.get('pathway_id')
            phone_number = data.get("to")
            
            if pathway_id and phone_number:
                background_tasks.add_task(schedule_follow_up_call, phone_number, pathway_id, call_id)
            else:
                logger.warning(f"⚠️ Cannot schedule follow-up for call {call_id}: missing pathway_id or phone_number in webhook data.")

        return {"status": "success", "message": "Call processed", "call_id": call_id}

    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def create_call(request: SendCallRequest):
    """Send a single AI phone call. Now includes analysis request."""
    try:
        url = "https://api.bland.ai/v1/calls"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}", "Content-Type": "application/json"}
        payload = request.model_dump(exclude_none=True)
        # Ensure analysis is requested to get a good summary/transcript
        payload['analysis_schema'] = {"transcript": "string", "summary": "string"}
        
        logger.info(f"📞 Sending call to {request.phone_number}")
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
    logger.info(f"📤 Starting batch call job for {len(request.calls)} numbers.")
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
            response = await create_call(single_call_request)
            responses.append({"status": "success", "data": response})
        except Exception as e:
            logger.error(f"❌ Failed to send call to {call_item.phone_number} in batch: {e}")
            responses.append({"status": "error", "phone_number": call_item.phone_number, "detail": str(e)})
            
    return {"status": "Batch job completed", "results": responses}

async def get_calls_from_db(db: Session, limit: int = 50, skip: int = 0):
    """Get call history from the database."""
    try:
        return db_get_calls(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"❌ Error fetching calls from DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch calls")
