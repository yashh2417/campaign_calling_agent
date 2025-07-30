import uuid
import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from core.config import settings
from core.database import logger
from crud.db_campaign import get_campaign_by_id, update_campaign_batch_id # <-- Add the new import
from crud.db_contact import get_contacts_by_ids
from schemas.call_data_schemas import BatchCallRequest

async def start_campaign_calls(request: BatchCallRequest, db: Session):
    """
    Starts a campaign by creating a single batch of calls using the Bland AI v2 batch API.
    """
    campaign = get_campaign_by_id(db, request.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not campaign.contact_list:
        raise HTTPException(status_code=400, detail="Campaign has no contacts")

    contacts = get_contacts_by_ids(db, campaign.contact_list)
    if not contacts:
        raise HTTPException(status_code=400, detail="No valid contacts found for this campaign.")

    # 1. Prepare the list of call objects for the batch
    call_objects = []
    for contact in contacts:
        # The task personalization still happens for each contact
        personalized_task = campaign.task.replace("{contact_name}", contact.name)
        
        call_objects.append({
            "phone_number": contact.phone_number,
            # We override the global task with the personalized one for each call
            "task": personalized_task,
        })

    # 2. Set the start time for the batch
    # As per your docs, this must be at least 30 mins in the future.
    start_time_utc = datetime.now(timezone.utc) + timedelta(minutes=31)

    # 3. Construct the payload with the correct structure for the v2 batch API
    batch_payload = {
        "global": {
            # The campaign's main task is the global prompt
            "task": campaign.task,
            "voice": campaign.voice,
            "start_time": start_time_utc.isoformat(),
            # Make sure WEBHOOK_URL is set in your .env and config files
            "webhook": settings.WEBHOOK_URL,
            "record": True,
            # The campaign_id from your DB is passed as metadata for tracking
            "metadata": { "campaign_id": str(campaign.campaign_id) }
        },
        "call_objects": call_objects
    }

    # 4. Make a single API call to the batch endpoint
    try:
        url = "https://api.bland.ai/v2/batches/create"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}", "Content-Type": "application/json"}
        
        logger.info(f"📤 Sending batch request for campaign '{campaign.campaign_name}' with {len(call_objects)} calls.")
        
        response = requests.post(url, json=batch_payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        response_data = response.json()
        # The actual batch_id created by Bland AI
        batch_id = response_data.get("data", {}).get("batch_id")

        logger.info(f"✅ Batch created successfully with batch_id: {batch_id}")

        if batch_id:
            update_campaign_batch_id(db, campaign_id=campaign.campaign_id, batch_id=batch_id)
        
        # Here you could update your campaign record in the DB with this new batch_id if needed
        # campaign.latest_batch_id = batch_id
        # db.commit()

        return {"status": "success", "message": "Campaign batch created successfully.", "batch_id": batch_id}

    except requests.exceptions.HTTPError as http_err:
        error_detail = http_err.response.text
        logger.error(f"❌ HTTP error creating batch: {http_err} - {error_detail}")
        raise HTTPException(status_code=http_err.response.status_code, detail=f"HTTP error from Bland AI: {error_detail}")
    except Exception as e:
        logger.error(f"❌ Unexpected error creating batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")