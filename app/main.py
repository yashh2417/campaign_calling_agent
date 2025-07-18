from fastapi import FastAPI, Request
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import create_db_and_tables
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from core.config import settings
from api.routes import router as api_router
from core.templates import templates

app = FastAPI(
    title="Bland AI Call Dashboard",
    description="Dashboard for managing AI-powered phone calls",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# DB connection on startup
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Homepage 
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the dashboard homepage"""
    return templates.TemplateResponse("index.html", {"request": request})

# Routers for your API
app.include_router(api_router)

# Run if main
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)