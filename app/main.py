import logging
import time
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from logging.handlers import RotatingFileHandler
from core.database import create_db_and_tables, get_db
from core.templates import templates
from sqlalchemy.orm import Session
from fastapi import Depends

# Import routers
try:
    from api import campaign_routes, contact_routes, routes, features_routes, user_routes
except ImportError as e:
    logging.error(f"Error importing routes: {e}")
    # Try importing individually to identify the problematic module
    try:
        from api import campaign_routes
        logging.info("✅ campaign_routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing campaign_routes: {e}")
    
    try:
        from api import contact_routes
        logging.info("✅ contact_routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing contact_routes: {e}")
    
    try:
        from api import routes
        logging.info("✅ routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing routes: {e}")
    
    try:
        from api import features_routes
        logging.info("✅ features_routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing features_routes: {e}")
    
    try:
        from api import user_routes
        logging.info("✅ user_routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing user_routes: {e}")

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

# Include API Routers with error handling
try:
    if 'routes' in locals():
        app.include_router(routes.router)
        logger.info("✅ Main routes included")
    else:
        logger.warning("⚠️ Main routes not available")
except Exception as e:
    logger.error(f"❌ Error including main routes: {e}")

try:
    if 'campaign_routes' in locals():
        app.include_router(campaign_routes.router)
        logger.info("✅ Campaign routes included")
    else:
        logger.warning("⚠️ Campaign routes not available")
except Exception as e:
    logger.error(f"❌ Error including campaign routes: {e}")

try:
    if 'contact_routes' in locals():
        app.include_router(contact_routes.router)
        logger.info("✅ Contact routes included")
    else:
        logger.warning("⚠️ Contact routes not available")
except Exception as e:
    logger.error(f"❌ Error including contact routes: {e}")

try:
    if 'features_routes' in locals():
        app.include_router(features_routes.router)
        logger.info("✅ Features routes included")
    else:
        logger.warning("⚠️ Features routes not available")
except Exception as e:
    logger.error(f"❌ Error including features routes: {e}")

try:
    if 'user_routes' in locals():
        app.include_router(user_routes.router)
        logger.info("✅ User routes included")
    else:
        logger.warning("⚠️ User routes not available")
except Exception as e:
    logger.error(f"❌ Error including user routes: {e}")

# Frontend Route
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the campaign dashboard homepage"""
    return templates.TemplateResponse("index.html", {"request": request})

# Add a simple test endpoint to verify the app is working
@app.get("/test")
def test_endpoint():
    """Simple test endpoint"""
    return {"status": "ok", "message": "API is working"}

# Add debug endpoints if needed
@app.get("/debug/routes")
def debug_routes():
    """Show which routes are loaded"""
    routes_info = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes_info.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else []
            })
    return {"routes": routes_info}