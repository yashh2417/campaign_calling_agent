from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load .env variables
load_dotenv()

# Configure FastAPI
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB setup
client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
db = client[os.getenv("MONGODB_DB_NAME", "bland_calls")]
calls_collection = db["calls"]

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/embedding-001")

# Define base directory
BASE_DIR = Path(__file__).resolve().parent

# Mount static and templates
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# Pinecone setup
pinecone_api_key = os.getenv("PINECONE_API_KEY")
if not pinecone_api_key:
    raise ValueError("Missing PINECONE_API_KEY in environment variables")

pc = Pinecone(api_key=pinecone_api_key)

# Ensure the index exists before using it
index_name = "bland-calls"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=768,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(index_name)

# Request schemas
class TranscriptItem(BaseModel):
    speaker: str
    text: str

class CallPayload(BaseModel):
    call_id: str
    transcript: List[TranscriptItem]
    summary: Optional[str] = None
    variables: Optional[dict] = None

class SendCallRequest(BaseModel):
    phone_number: str
    pathway_id: str
    variables: Optional[dict] = None
    task: Optional[str] = None
    record: Optional[bool] = None
    webhook: Optional[str] = None

class BatchCallRequestItem(BaseModel):
    phone_number: str
    variables: Optional[dict] = None

class BatchCallRequest(BaseModel):
    pathway_id: str
    calls: List[BatchCallRequestItem]
    task: Optional[str] = None
    record: Optional[bool] = None
    webhook: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/bland/postcall")
async def receive_postcall(request: Request):
    try:
        # 1. Log the full incoming payload
        data = await request.json()
        print("📥 Incoming Webhook Payload:", data)

        # 2. Extract and log each field
        call_id = data.get("call_id")
        transcript = data.get("transcripts", [])
        summary = data.get("summary")
        variables = data.get("variables", {})

        print("🆔 Call ID:", call_id)
        print("📄 Summary:", summary)
        print("📦 Variables:", variables)
        print("🎙️ Transcript Raw:", transcript)

        # 3. Validate and build transcript text
        if not isinstance(transcript, list) or not call_id:
            print("❌ Invalid transcript or call_id")
            return {"status": "error", "message": "Invalid data"}

        transcript_text = " ".join([
            f"{t.get('user', 'unknown')}: {t.get('text', '')}"
            for t in transcript
        ])
        print("📝 Transcript Text:", transcript_text)

        # 4. Fetch call analysis from Bland (optional)
        bland_api_key = os.getenv("BLAND_API_KEY")
        headers = {"Authorization": bland_api_key}
        analysis_url = f"https://api.bland.ai/v1/calls/{call_id}/analyze"
        analysis_response = requests.get(analysis_url, headers=headers)
        analysis_data = analysis_response.json() if analysis_response.ok else None
        print("📊 Analysis:", analysis_data)

        # 5. Insert into MongoDB
        call_record = {
            "call_id": call_id,
            "summary": summary,
            "variables": variables,
            "transcript_text": transcript_text,
            "analysis": analysis_data
        }

        try:
            await calls_collection.insert_one(call_record)
            print("✅ Inserted into MongoDB")
        except Exception as e:
            print("❌ Mongo insert error:", e)

        # 6. Embed and upsert into Pinecone
        embed_response = model.embed_content(
            contents=[transcript_text],
            task_type="RETRIEVAL_QUERY"
        )
        embedding = embed_response.get("embedding")
        if not embedding:
            print("❌ Embedding failed")
            return {"status": "error", "message": "Embedding not generated"}

        index.upsert([
            (call_id, embedding, {
                "text": transcript_text,
                **variables
            })
        ])
        print("✅ Upserted into Pinecone")

        return {"status": "success", "message": "Call processed successfully"}

    except Exception as e:
        print("❌ Exception occurred:", str(e))
        return {"status": "error", "message": str(e)}

@app.post("/bland/sendcall")
async def send_call(request: SendCallRequest):
    url = "https://api.bland.ai/v1/calls"
    headers = {
        "Authorization": os.getenv("BLAND_API_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "phone_number": request.phone_number,
        "pathway_id": request.pathway_id,
        "variables": request.variables or {}
    }

    if request.task:
        payload["task"] = request.task
    if request.record is not None:
        payload["record"] = request.record
    if request.webhook:
        payload["webhook"] = request.webhook


    response = requests.post(url, json=payload, headers=headers)

    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {
            "status": "error",
            "detail": f"HTTP error occurred: {http_err}",
            "response_text": response.text
        }
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "error",
            "detail": "Response was not valid JSON",
            "response_text": response.text
        }

@app.post("/bland/sendbatch")
async def send_batch(request: BatchCallRequest):
    url = "https://api.bland.ai/v2/batches/create"
    headers = {
        "Authorization": os.getenv("BLAND_API_KEY"),
        "Content-Type": "application/json"
    }

    global_payload = {
        "pathway_id": request.pathway_id
    }
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

    response = requests.post(url, json=payload, headers=headers)
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        return {
            "status": "error",
            "detail": f"HTTP error occurred: {http_err}",
            "response_text": response.text
        }
    except requests.exceptions.JSONDecodeError:
        return {
            "status": "error",
            "detail": "Response was not valid JSON",
            "response_text": response.text
        }
