import logging
import sys
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# This ensures that SQLAlchemy's Base metadata is aware of your models
from models.call_table import Call

# This will capture logs from all modules in your application.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import create_db_and_tables
from core.config import settings
from api.routes import router as api_router
from core.templates import templates

app = FastAPI(
    title="Bland AI Call Dashboard",
    description="Dashboard for managing AI-powered phone calls",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Database connection on startup
@app.on_event("startup")
def on_startup():
    """
    This function runs when the FastAPI application starts.
    It will now correctly see the `Call` model and create the table if it doesn't exist.
    """
    logger = logging.getLogger(__name__)
    logger.info("🚀 Application startup: Attempting to create database and tables...")
    create_db_and_tables()

# Homepage Route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the dashboard homepage"""
    return templates.TemplateResponse("index.html", {"request": request})

# Include API routes from api/routes.py
app.include_router(api_router)

# This block is for running the app locally with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
