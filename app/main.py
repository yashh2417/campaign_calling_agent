import logging
import time
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from logging.handlers import RotatingFileHandler
from core.database import create_db_and_tables, get_db
from api import campaign_routes, contact_routes, routes, features_routes, user_routes
from core.templates import templates
from sqlalchemy.orm import Session
from fastapi import Depends

# This is important: it ensures SQLAlchemy knows about your models before creating tables.
from models import campaign, contact, call_table, user

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('app.log', maxBytes=10485760, backupCount=5),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Lead Generation AI", version="1.0.0")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.method} {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "detail": str(exc)}
    )

# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(f"{request.method} {request.url} - {response.status_code} - {process_time:.4f}s")
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.on_event("startup")
def on_startup():
    logger.info("🚀 Application startup: Creating database and tables...")
    create_db_and_tables()

# Health check endpoint
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )

# API Routers
app.include_router(routes.router)
app.include_router(campaign_routes.router)
app.include_router(contact_routes.router)
app.include_router(features_routes.router)
app.include_router(user_routes.router)

# Frontend Route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the campaign dashboard homepage"""
    return templates.TemplateResponse("index.html", {"request": request})