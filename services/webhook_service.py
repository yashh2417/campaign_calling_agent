import requests
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from core.config import settings
from core.database import logger
from crud.db_call import create_call as db_create_call
from schemas.call_data_schemas import CallCreate
from services.embedding_service import generate_embedding
from services.followup_service import schedule_follow_up_call, parse_follow_up_time

async def get_postcall_data(request: Request, db: Session, background_tasks: BackgroundTasks):
    """
    Receives and processes webhook callbacks from Bland AI.
    It enriches the data, saves it to the DB, and triggers follow-ups.
    """
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")

        call_id = data.get("call_id")
        if not call_id: raise HTTPException(status_code=400, detail="Missing call_id")

        transcript_text = data.get("concatenated_transcript", "").strip()
        if not transcript_text:
            transcript_text = " ".join([f"{t.get('user', 'unknown')}: {t.get('text', '')}" for t in data.get("transcripts", [])])

        emotion, follow_up_time_str = "unknown", None
        if settings.BLAND_API_KEY:
            try:
                headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}"}
                analysis_url = f"https://api.bland.ai/v1/calls/{call_id}/analyze"
                analysis_payload = {
                    "goal": "Determine sentiment and extract a specific follow-up time if mentioned, converting it to a standard format.",
                    "questions": [
                        ["What was the overall sentiment of the person who was called?", "Answer with only one word: positive, neutral, or negative."],
                        ["Did the user suggest a specific time to call back (e.g., 'tomorrow at 3pm', 'next Friday')? If so, convert it to an ISO 8601 timestamp (YYYY-MM-DDTHH:MM:SS). If not, answer 'No'.", "string"]
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
        
        metadata = data.get('metadata', {})
        batch_id = metadata.get('batch_id')
        pathway_id_for_followup = metadata.get('pathway_id')

        # calculate and set follow-up data 
        followup_scheduled = False
        followup_dt = None
        
        if emotion == "neutral":
            phone_number = data.get("to")
            if pathway_id_for_followup and phone_number:
                delay = parse_follow_up_time(follow_up_time_str)
                if delay > 0:
                    followup_scheduled = True
                    # Calculate the exact UTC datetime for the follow-up
                    followup_dt = datetime.now(timezone.utc) + timedelta(seconds=delay)
                    background_tasks.add_task(schedule_follow_up_call, phone_number, pathway_id_for_followup, call_id, delay)
                else:
                    logger.warning(f"⚠️ Calculated follow-up delay for call {call_id} is zero or negative. Skipping.")
            else:
                logger.warning(f"⚠️ Cannot schedule follow-up for call {call_id}: missing 'pathway_id' in webhook metadata or 'to' phone number.")

        call_to_create = CallCreate(
            call_id=call_id, batch_id=batch_id, to_phone=data.get("to"), from_phone=data.get("from"),
            summary=data.get("summary"), call_transcript=transcript_text, completed=data.get("completed"),
            emotion=emotion, embedding=embedding_vector,
            # follow-up data to be saved in the database
            followup_scheduled=followup_scheduled,
            followup_datetime=followup_dt
        )
        db_create_call(db=db, call=call_to_create)

        return {"status": "success", "message": "Call processed", "call_id": call_id}

    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
