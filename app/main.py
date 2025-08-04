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
from fastapi.templating import Jinja2Templates
import os
from api import (
    auth_routes,
    campaign_routes,
    contact_routes,
    dashboard_routes,
    features_routes,
    routes,
    user_routes,
    campaign_management_routes
)

# Import routers
try:
    from api import campaign_routes, contact_routes, routes, features_routes, user_routes, auth_routes
    # Import new authentication and dashboard routes
    from api import auth_routes, dashboard_routes, campaign_management_routes
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

    # Try importing new routes
    try:
        from api import auth_routes
        logging.info("✅ auth_routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing auth_routes: {e}")
    
    try:
        from api import dashboard_routes
        logging.info("✅ dashboard_routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing dashboard_routes: {e}")
    
    try:
        from api import campaign_management_routes  
        logging.info("✅ campaign_management_routes imported successfully")
    except ImportError as e:
        logging.error(f"❌ Error importing campaign_management_routes: {e}")

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

app = FastAPI(
    title="EICE-AIM - AI Campaign Management System", 
    version="2.0.0",
    description="Advanced AI-powered campaign management with user authentication"
)

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

# CORS Middleware - Updated for better security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"],  # More specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.on_event("startup")
def on_startup():
    logger.info("🚀 Application startup: Creating database and tables...")
    create_db_and_tables()
    logger.info("🔐 Authentication system enabled")

# Health check endpoint
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy", 
            "database": "connected", 
            "timestamp": time.time(),
            "version": "2.0.0",
            "features": ["authentication", "campaigns", "contacts", "voice_testing"]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )

# Include Authentication Routes (NEW)
try:
    if 'auth_routes' in locals():
        app.include_router(auth_routes.router)
        logger.info("✅ Authentication routes included")
    else:
        logger.warning("⚠️ Authentication routes not available")
except Exception as e:
    logger.error(f"❌ Error including authentication routes: {e}")

# Include Dashboard Routes (NEW)
try:
    if 'dashboard_routes' in locals():
        app.include_router(dashboard_routes.router)
        logger.info("✅ Dashboard routes included")
    else:
        logger.warning("⚠️ Dashboard routes not available")
except Exception as e:
    logger.error(f"❌ Error including dashboard routes: {e}")

# Include Campaign Management Routes (NEW)
try:
    if 'campaign_management_routes' in locals():
        app.include_router(campaign_management_routes.router)
        logger.info("✅ Campaign management routes included")
    else:
        logger.warning("⚠️ Campaign management routes not available")
except Exception as e:
    logger.error(f"❌ Error including campaign management routes: {e}")

# Include Existing API Routers with error handling
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


app.include_router(auth_routes.router)
app.include_router(campaign_routes.router)
app.include_router(contact_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(features_routes.router)
app.include_router(routes.router)
app.include_router(user_routes.router)
app.include_router(campaign_management_routes.router)


# Frontend Route - Updated to serve the new frontend
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the enhanced campaign dashboard with authentication"""
    # For now, we'll serve the HTML directly
    # In production, you might want to use templates
    return templates.TemplateResponse("frontend.html", {"request": request})

# Alternative template-based approach (if you prefer using templates)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the dashboard using templates"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# API Information Endpoint
@app.get("/api/info")
def api_info():
    """Get API information and available endpoints"""
    return {
        "name": "EICE-AIM API",
        "version": "2.0.0",
        "description": "AI Campaign Management System with Authentication",
        "features": [
            "User Authentication & Registration",
            "Campaign Management with Versioning", 
            "Contact Management with CSV Import",
            "AI Voice Testing with Bland AI Integration",
            "Call History & Analytics",
            "Real-time Dashboard"
        ],
        "endpoints": {
            "authentication": "/api/auth/*",
            "dashboard": "/api/dashboard/*", 
            "campaigns": "/api/campaigns/* & /api/campaign-management/*",
            "contacts": "/api/contacts/*",
            "calls": "/api/calls/*",
            "features": "/api/features/*",
            "users": "/api/users/*"
        },
        "documentation": "/docs",
        "health_check": "/health"
    }

# Add a simple test endpoint to verify the app is working
@app.get("/test")
def test_endpoint():
    """Simple test endpoint"""
    return {
        "status": "ok", 
        "message": "EICE-AIM API is working",
        "version": "2.0.0",
        "timestamp": time.time()
    }

# Add debug endpoints if needed
@app.get("/debug/routes")
def debug_routes():
    """Show which routes are loaded"""
    routes_info = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes_info.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, 'name', 'unnamed')
            })
    return {"routes": routes_info}

@app.get("/debug/auth-test") 
def debug_auth_test():
    """Test endpoint for authentication debugging"""
    return {
        "message": "This endpoint can be used to test authentication",
        "auth_routes_available": 'auth_routes' in locals(),
        "timestamp": time.time()
    }

# Additional utility endpoints
@app.get("/api/version")
def get_version():
    """Get API version information"""
    return {
        "version": "2.0.0",
        "name": "EICE-AIM",
        "description": "AI Campaign Management System",
        "build_date": "2024-01-01",
        "features": {
            "authentication": True,
            "campaigns": True,
            "contacts": True,
            "voice_testing": True,
            "call_history": True,
            "dashboard": True
        }
    }