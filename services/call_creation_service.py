import uuid
import requests
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.config import settings
from core.database import logger
from crud.db_call import get_calls as db_get_calls
from schemas.call_data_schemas import SendCallRequest, BatchCallRequest

async def create_call(request: SendCallRequest, batch_id: str = None):
    """
    Sends a single AI phone call to the Bland AI API.
    Injects custom IDs into the metadata for tracking.
    """
    try:
        url = "https://api.bland.ai/v1/calls"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}", "Content-Type": "application/json"}
        
        # Use the metadata field to pass custom data that will be returned in the webhook.
        request.metadata = {
            "pathway_id": request.pathway_id
        }
        if batch_id:
            request.metadata["batch_id"] = batch_id
            
        payload = request.model_dump(exclude_none=True)
        # Request analysis to ensure we get a transcript and summary back.
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
    """
    Sends a batch of AI phone calls by creating a batch ID and sending each call individually.
    """
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
    """
    Retrieves a list of call records from the database.
    """
    try:
        return db_get_calls(db, skip=skip, limit=limit)
    except Exception as e:
        logger.error(f"❌ Error fetching calls from DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch calls")
