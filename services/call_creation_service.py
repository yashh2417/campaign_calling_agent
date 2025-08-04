import uuid
import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from core.config import settings
from core.database import logger
from crud.db_campaign import get_campaign_by_id, update_campaign_batch_id
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
        # The task personalization happens for each contact
        personalized_task = (campaign.task or "").replace("{contact_name}", contact.name)
        
        call_objects.append({
            "phone_number": contact.phone_number,
            "task": personalized_task,
            # Add metadata for each call to track it back to the campaign
            "metadata": {
                "contact_id": str(contact.id),
                "contact_name": contact.name,
                "campaign_id": str(campaign.campaign_id)
            }
        })

    # 2. Determine the start time for the batch
    now_utc = datetime.now(timezone.utc)
    
    if campaign.start_date:
        # Use the campaign's scheduled start time
        if campaign.start_date.tzinfo is None:
            # If timezone-naive, assume UTC
            start_time_utc = campaign.start_date.replace(tzinfo=timezone.utc)
        else:
            start_time_utc = campaign.start_date.astimezone(timezone.utc)
            
        # Check if the scheduled time is at least 30 minutes in the future
        min_start_time = now_utc + timedelta(minutes=2)
        if start_time_utc < min_start_time:
            logger.warning(f"⚠️ Scheduled start time {start_time_utc} is less than 30 minutes from now. Using minimum required time.")
            start_time_utc = min_start_time
    else:
        # Default to 30 minutes from now (minimum required by Bland AI)
        start_time_utc = now_utc + timedelta(minutes=2)

    logger.info(f"📅 Batch scheduled to start at: {start_time_utc.isoformat()}")

    # 3. Construct the payload with the correct structure for the v2 batch API
    batch_payload = {
        "call_objects": call_objects,
        "global": {
            "task": campaign.task or "Make a call to the contact.",
            "voice": campaign.voice or "maya",
            "start_time": start_time_utc.isoformat(),
            "webhook": settings.WEBHOOK_URL,
            "record": True,
            "metadata": {
                "campaign_id": str(campaign.campaign_id),
                "campaign_name": campaign.campaign_name,
                "batch_created_at": now_utc.isoformat()
            }
        }
    }

    # 4. Make a single API call to the batch endpoint
    try:
        url = "https://api.bland.ai/v2/batches/create"  # Correct endpoint
        headers = {
            "Authorization": f"Bearer {settings.BLAND_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        logger.info(f"📤 Sending batch request for campaign '{campaign.campaign_name}' with {len(call_objects)} calls.")
        logger.info(f"🔗 Using webhook URL: {settings.WEBHOOK_URL}")
        
        response = requests.post(url, json=batch_payload, headers=headers, timeout=60)
        
        # Log the full response for debugging
        logger.info(f"📥 Bland AI Response Status: {response.status_code}")
        logger.info(f"📥 Bland AI Response Body: {response.text}")
        
        response.raise_for_status()
        
        response_data = response.json()
        
        # Extract batch_id from response (handle nested structure)
        batch_id = None
        if "batch_id" in response_data:
            batch_id = response_data["batch_id"]
        elif "data" in response_data and isinstance(response_data["data"], dict):
            batch_id = response_data["data"].get("batch_id")
        
        if batch_id:
            logger.info(f"✅ Batch created successfully with batch_id: {batch_id}")
            # Update the campaign with the batch_id
            update_campaign_batch_id(db, campaign_id=campaign.campaign_id, batch_id=batch_id)
        else:
            logger.warning("⚠️ Batch created but no batch_id returned in response")

        return {
            "status": "success", 
            "message": f"Campaign batch created successfully. {len(call_objects)} calls scheduled.", 
            "batch_id": batch_id,
            "start_time": start_time_utc.isoformat(),
            "call_count": len(call_objects),
            "response_data": response_data  # Include full response for debugging
        }

    except requests.exceptions.HTTPError as http_err:
        error_detail = "Unknown HTTP error"
        try:
            error_response = http_err.response.json()
            error_detail = error_response.get("message", error_response.get("error", http_err.response.text))
        except:
            error_detail = http_err.response.text
            
        logger.error(f"❌ HTTP error creating batch: {http_err} - {error_detail}")
        raise HTTPException(
            status_code=http_err.response.status_code, 
            detail=f"Bland AI API error: {error_detail}"
        )
    except requests.exceptions.Timeout:
        logger.error("❌ Request to Bland AI timed out")
        raise HTTPException(status_code=504, detail="Request to Bland AI timed out")
    except requests.exceptions.RequestException as req_err:
        logger.error(f"❌ Request error: {req_err}")
        raise HTTPException(status_code=502, detail="Failed to connect to Bland AI")
    except Exception as e:
        logger.error(f"❌ Unexpected error creating batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")