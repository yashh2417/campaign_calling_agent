from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import requests
from dotenv import load_dotenv
from pathlib import Path
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env variables
load_dotenv()

# Configure FastAPI
app = FastAPI(
    title="Bland AI Call Dashboard",
    description="Dashboard for managing AI-powered phone calls",
    version="1.0.0"
)

# Add CORS middleware with more restrictive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

MONGODB_URL = os.getenv("MONGODB_URL")

if not MONGODB_URL:
    logger.error("❌ MONGODB_URL environment variable not set")
    raise ValueError("MONGODB_URL environment variable is required but not set")

logger.info(f"🔗 Connecting to MongoDB using: {MONGODB_URL}")  

# MongoDB setup
try:
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[os.getenv("MONGODB_DB_NAME")]
    calls_collection = db["calls"]
except Exception as e:
    logger.error(f"MongoDB connection failed: {e}")
    raise

# Define base directory
BASE_DIR = Path(__file__).resolve().parent

# Mount static and templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Request schemas
class TranscriptItem(BaseModel):
    speaker: str
    text: str

class CallPayload(BaseModel):
    call_id: str
    transcript: List[TranscriptItem]
    summary: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None

class SendCallRequest(BaseModel):
    phone_number: str
    pathway_id: Optional[str] = None 
    variables: Optional[Dict[str, Any]] = None
    task: Optional[str] = None
    record: Optional[bool] = None
    webhook: Optional[str] = None

    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Basic phone number validation
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

    @validator('pathway_id')
    def validate_pathway_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Pathway ID cannot be empty')
        return v.strip()

class BatchCallRequestItem(BaseModel):
    phone_number: str
    variables: Optional[Dict[str, Any]] = None

    @validator('phone_number')
    def validate_phone_number(cls, v):
        if not re.match(r'^\+?[1-9]\d{1,14}$', v):
            raise ValueError('Invalid phone number format')
        return v

class BatchCallRequest(BaseModel):
    pathway_id: Optional[str] = None
    calls: List[BatchCallRequestItem]
    task: Optional[str] = None
    record: Optional[bool] = None
    webhook: Optional[str] = None

    @validator('pathway_id')
    def validate_pathway_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Pathway ID cannot be empty')
        return v.strip()

    @validator('calls')
    def validate_calls(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one call is required')
        if len(v) > 100:  # Reasonable limit
            raise ValueError('Too many calls in batch (max 100)')
        return v

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the dashboard homepage"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/bland/postcall")
async def receive_postcall(request: Request):
    """Receive and process webhook callbacks from Bland AI"""
    try:
        data = await request.json()
        logger.info(f"📥 Incoming Webhook Payload: {data}")

        call_id = data.get("call_id")
        transcript = data.get("transcripts", [])
        summary = data.get("summary")
        variables = data.get("variables", {})

        logger.info(f"🆔 Call ID: {call_id}")
        logger.info(f"📄 Summary: {summary}")
        logger.info(f"📦 Variables: {variables}")

        if not call_id:
            logger.error("❌ Missing call_id in webhook payload")
            raise HTTPException(status_code=400, detail="Missing call_id")

        if not isinstance(transcript, list):
            logger.error("❌ Invalid transcript format")
            raise HTTPException(status_code=400, detail="Invalid transcript format")

        # Process transcript
        transcript_text = ""
        if transcript:
            transcript_text = " ".join([
                f"{t.get('user', 'unknown')}: {t.get('text', '')}"
                for t in transcript if isinstance(t, dict)
            ])
        
        logger.info(f"📝 Transcript Text: {transcript_text}")

        # Call Bland AI analysis endpoint
        analysis_data = None
        bland_api_key = os.getenv("BLAND_API_KEY")
        
        if bland_api_key and call_id:
            try:
                headers = {"Authorization": f"Bearer {bland_api_key}"}
                analysis_url = f"https://api.bland.ai/v1/calls/{call_id}/analyze"
                analysis_payload = {
                    "goal": "Understand customer's interest in real estate projects and satisfaction level",
                    "questions": [
                        ["Who answered the call?", "human or voicemail"],
                        ["Positive feedback about the product", "string"],
                        ["Negative feedback about the product", "string"],
                        ["Customer confirmed they were satisfied", "boolean"],
                        ["Customer showed interest in the product", "boolean"],
                        ["Follow-up required", "boolean"]
                    ]
                }

                analysis_response = requests.post(
                    analysis_url, 
                    json=analysis_payload, 
                    headers=headers,
                    timeout=30
                )
                
                if analysis_response.status_code == 200:
                    analysis_data = analysis_response.json()
                    logger.info(f"📊 Analysis successful: {analysis_data}")
                else:
                    logger.error(f"❌ Analysis API error: {analysis_response.status_code} - {analysis_response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Analysis request failed: {e}")
            except Exception as e:
                logger.error(f"❌ Analysis processing error: {e}")

        # Prepare call record
        call_record = {
            "call_id": call_id,
            "summary": summary,
            "variables": variables,
            "transcript_text": transcript_text,
            "raw_transcript": transcript,
            "analysis": analysis_data,
            "created_at": {"$date": {"$numberLong": str(int(__import__('time').time() * 1000))}}
        }

        # Insert into MongoDB
        try:
            result = await calls_collection.insert_one(call_record)
            logger.info(f"✅ Inserted into MongoDB with ID: {result.inserted_id}")
        except Exception as e:
            logger.error(f"❌ MongoDB insert error: {e}")
            raise HTTPException(status_code=500, detail="Database error")

        return {
            "status": "success", 
            "message": "Call processed successfully",
            "call_id": call_id,
            "analysis_available": analysis_data is not None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in webhook processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/bland/sendcall")
async def send_call(request: SendCallRequest):
    """Send a single AI phone call"""
    try:
        url = "https://api.bland.ai/v1/calls"
        bland_api_key = os.getenv("BLAND_API_KEY")
        
        if not bland_api_key:
            raise HTTPException(status_code=500, detail="BLAND_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {bland_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "phone_number": request.phone_number,
            "pathway_id": request.pathway_id,
            "variables": request.variables or {}
        }

        # Add optional fields only if they have values
        if request.task:
            payload["task"] = request.task
        if request.record is not None:
            payload["record"] = request.record
        if request.webhook:
            payload["webhook"] = request.webhook

        logger.info(f"📞 Sending call to {request.phone_number}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✅ Call sent successfully: {result}")
        
        return result

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"❌ HTTP error: {http_err}")
        error_detail = f"HTTP error occurred: {http_err}"
        if hasattr(http_err, 'response') and http_err.response:
            error_detail += f" - {http_err.response.text}"
        raise HTTPException(status_code=400, detail=error_detail)
    
    except requests.exceptions.Timeout:
        logger.error("❌ Request timeout")
        raise HTTPException(status_code=408, detail="Request timeout")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send call")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/bland/sendbatch")
async def send_batch(request: BatchCallRequest):
    """Send batch AI phone calls"""
    try:
        url = "https://api.bland.ai/v2/batches/create"
        bland_api_key = os.getenv("BLAND_API_KEY")
        
        if not bland_api_key:
            raise HTTPException(status_code=500, detail="BLAND_API_KEY not configured")
        
        headers = {
            "Authorization": f"Bearer {bland_api_key}",
            "Content-Type": "application/json"
        }

        global_payload = {
            "pathway_id": request.pathway_id
        }
        
        # Add optional global fields only if they have values
        if request.task:
            global_payload["task"] = request.task
        if request.record is not None:
            global_payload["record"] = request.record
        if request.webhook:
            global_payload["webhook"] = request.webhook

        payload = {
            "global": global_payload,
            "call_objects": [
                {
                    "phone_number": call.phone_number,
                    "variables": call.variables or {}
                }
                for call in request.calls
            ]
        }

        logger.info(f"📞 Sending batch of {len(request.calls)} calls")
        
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"✅ Batch sent successfully: {result}")
        
        return result

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"❌ HTTP error: {http_err}")
        error_detail = f"HTTP error occurred: {http_err}"
        if hasattr(http_err, 'response') and http_err.response:
            error_detail += f" - {http_err.response.text}"
        raise HTTPException(status_code=400, detail=error_detail)
    
    except requests.exceptions.Timeout:
        logger.error("❌ Request timeout")
        raise HTTPException(status_code=408, detail="Request timeout")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request error: {e}")
        raise HTTPException(status_code=500, detail="Failed to send batch")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/calls")
async def get_calls(limit: int = 50, skip: int = 0):
    """Get call history from database"""
    try:
        cursor = calls_collection.find().sort("created_at", -1).skip(skip).limit(limit)
        calls = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        for call in calls:
            if "_id" in call:
                call["_id"] = str(call["_id"])
        
        return {"calls": calls, "count": len(calls)}
    
    except Exception as e:
        logger.error(f"❌ Error fetching calls: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch calls")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)