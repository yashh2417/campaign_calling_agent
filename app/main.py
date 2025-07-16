from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
import uuid
import os
import requests
from dotenv import load_dotenv

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import Request
from fastapi.templating import Jinja2Templates

# Load .env variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("models/embedding-001")

# Configure FastAPI
app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# MySQL setup from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL in environment variables")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
        dimension=768,  # Gemini embedding dim is usually 768
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(index_name)

# SQLAlchemy model
class Call(Base):
    __tablename__ = "calls"
    call_id = Column(String(255), primary_key=True, index=True)
    summary = Column(Text)
    variables = Column(JSON)
    transcript_text = Column(Text)
    analysis = Column(JSON)  # Add analysis column

Base.metadata.create_all(bind=engine)

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

class BatchCallRequestItem(BaseModel):
    phone_number: str
    # pathway_id: str
    variables: Optional[dict] = None

class BatchCallRequest(BaseModel):
    pathway_id: str
    calls: List[BatchCallRequestItem]

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/bland/postcall")
async def receive_postcall(payload: CallPayload):
    db = SessionLocal()

    # Prepare text and summary
    transcript_text = " ".join([f"{t.speaker}: {t.text}" for t in payload.transcript])
    summary = payload.summary

    # if not summary:
    #     response = genai.GenerativeModel("gemini-2.0-flash").generate_content(
    #         f"Summarize the following transcript: {transcript_text}"
    #     )
    #     summary = response.text

    # Fetch analysis from Bland
    bland_api_key = os.getenv("BLAND_API_KEY")
    headers = {"Authorization": bland_api_key}
    analysis_url = f"https://api.bland.ai/v1/calls/{payload.call_id}/analyze"
    analysis_response = requests.get(analysis_url, headers=headers)
    analysis_data = analysis_response.json() if analysis_response.ok else None

    # Store in MySQL
    call_record = Call(
        call_id=payload.call_id,
        summary=summary,
        variables=payload.variables,
        transcript_text=transcript_text,
        analysis=analysis_data
    )
    db.add(call_record)
    db.commit()
    db.close()

    # Create embedding and upsert to Pinecone
    embed_response = model.embed_content(
        contents=[transcript_text],
        task_type="RETRIEVAL_QUERY"
    )
    embedding = embed_response["embedding"]

    index.upsert([
        (payload.call_id, embedding, {
            "text": transcript_text,
            **(payload.variables or {})
        })
    ])

    return {"status": "success", "message": "Data stored in MySQL and Pinecone."}

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

    payload = {
        "global": {
            "pathway_id": request.pathway_id
        },
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
