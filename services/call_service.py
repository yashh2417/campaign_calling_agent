import time
import requests
import uuid
import re
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from core.config import settings
from core.database import logger
from crud.db_call import create_call as db_create_call, get_calls as db_get_calls
from schemas.call_data_schemas import CallCreate, SendCallRequest, BatchCallRequest
from services.embedding_service import generate_embedding

# --- Follow-up Call Logic ---

async def schedule_follow_up_call(phone_number: str, pathway_id: str, original_call_id: str, delay_seconds: int):
    """
    Waits for a specified duration (in seconds) and then places a follow-up call.
    """
    logger.info(f"⏰ Scheduling follow-up call to {phone_number} in {delay_seconds / 60:.1f} minutes for original call {original_call_id}.")
    time.sleep(delay_seconds)
    
    logger.info(f"📞 Placing scheduled follow-up call to {phone_number}.")
    follow_up_request = SendCallRequest(
        phone_number=phone_number,
        pathway_id=pathway_id,
        task=f"Follow-up call for original call ID: {original_call_id}. This call was scheduled based on the user's request.",
        webhook="https://campaign-calling-agent-latest.onrender.com/bland/postcall"
    )
    
    try:
        await create_call(follow_up_request)
    except Exception as e:
        logger.error(f"❌ Failed to place follow-up call to {phone_number}: {e}")

def parse_follow_up_time(time_string: str) -> int:
    """
    Parses a human-readable time string from the AI and returns the delay in seconds.
    Returns a default if the string is not understandable.
    """
    default_delay_seconds = 300  # 1 hour default
    if not isinstance(time_string, str): return default_delay_seconds
    time_string = time_string.lower().strip()
    if "tomorrow" in time_string: return 24 * 3600
    if match := re.search(r'(\d+)\s+hour', time_string): return int(match.group(1)) * 3600
    if match := re.search(r'(\d+)\s+minute', time_string): return int(match.group(1)) * 60
    logger.warning(f"⚠️ Could not parse follow-up time string '{time_string}'. Using default delay.")
    return default_delay_seconds

# --- Main Service Functions ---

async def get_postcall_data(request: Request, db: Session, background_tasks: BackgroundTasks):
    """
    Receive and process webhook callbacks from Bland AI, using metadata for custom IDs.
    """
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")

        call_id = data.get("call_id")
        if not call_id: raise HTTPException(status_code=400, detail="Missing call_id")

        transcript_text = data.get("concatenated_transcript", "").strip()

        emotion, follow_up_time_str = "unknown", None
        if settings.BLAND_API_KEY:
            try:
                # (Analysis logic remains the same)
                headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}"}
                analysis_url = f"https://api.bland.ai/v1/calls/{call_id}/analyze"
                analysis_payload = {
                    "goal": "Determine sentiment and extract a specific follow-up time if mentioned.",
                    "questions": [
                        ["What was the overall sentiment of the person who was called?", "Answer with only one word: positive, neutral, or negative."],
                        ["Did the user suggest a specific time to call back? If so, state the time (e.g., 'in 2 hours', 'tomorrow'). If not, answer 'No'.", "string"]
                    ]
                }
                analysis_response = requests.post(analysis_url, json=analysis_payload, headers=headers, timeout=30)
                if analysis_response.status_code == 200:
                    analysis_data = analysis_response.json()
                    logger.info(f"📊 Analysis successful: {analysis_data}")
                    answers = analysis_data.get('answers', [])
                    if len(answers) > 0: emotion = answers[0].lower().strip()
                    if len(answers) > 1: follow_up_time_str = answers[1]
                else:
                    logger.error(f"❌ Analysis API error: {analysis_response.status_code} - {analysis_response.text}")
            except Exception as e:
                logger.error(f"❌ Analysis request failed: {e}")

        embedding_vector = generate_embedding(transcript_text)
        
        # --- FIX: Extract custom IDs from the 'metadata' field ---
        metadata = data.get('metadata', {})
        batch_id = metadata.get('batch_id')
        pathway_id_for_followup = metadata.get('pathway_id')
        # --- END OF FIX ---

        call_to_create = CallCreate(
            call_id=call_id, batch_id=batch_id, to_phone=data.get("to"), from_phone=data.get("from"),
            summary=data.get("summary"), call_transcript=transcript_text, completed=data.get("completed"),
            emotion=emotion, embedding=embedding_vector
        )
        db_create_call(db=db, call=call_to_create)

        if emotion == "neutral":
            phone_number = data.get("to")
            if pathway_id_for_followup and phone_number:
                delay = parse_follow_up_time(follow_up_time_str)
                background_tasks.add_task(schedule_follow_up_call, phone_number, pathway_id_for_followup, call_id, delay)
            else:
                logger.warning(f"⚠️ Cannot schedule follow-up for call {call_id}: missing 'pathway_id' in webhook metadata or 'to' phone number.")

        return {"status": "success", "message": "Call processed", "call_id": call_id}

    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def create_call(request: SendCallRequest, batch_id: str = None):
    """Send a single AI phone call. This function correctly injects IDs into metadata."""
    try:
        url = "https://api.bland.ai/v1/calls"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}", "Content-Type": "application/json"}
        
        # --- FIX: Inject custom IDs into the 'metadata' field ---
        request.metadata = {
            "pathway_id": request.pathway_id
        }
        if batch_id:
            request.metadata["batch_id"] = batch_id
        # --- END OF FIX ---
            
        payload = request.model_dump(exclude_none=True)
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
                phone_number=call_item.phone_number, pathway_id=request.pathway_id,
                variables=call_item.variables, task=request.task, record=request.record,
                webhook=request.webhook
            )
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
