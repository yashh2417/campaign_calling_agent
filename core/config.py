import os
from dotenv import load_dotenv
from pathlib import Path
from typing import List

# --- Robust .env Loading Logic ---
# 1. Build an absolute path to the project's root directory.
#    This works no matter where you run the 'uvicorn' command from.
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"

# 2. Explicitly load the .env file from that absolute path.
#    If the file is found, its variables will be loaded into the environment.
if os.path.exists(env_path):
    print(f"INFO: Loading environment variables from: {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    print(f"WARNING: .env file not found at {env_path}. Relying on system environment variables.")
# --- End of Logic ---


class Settings:
    """
    Holds all the application settings, loaded from environment variables.
    """
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # API key for the Bland AI service
    BLAND_API_KEY: str = os.getenv("BLAND_API_KEY")
    
    # List of allowed origins for CORS
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000").split(",")
    
    # API key for Google Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")
    
    # Webhook configuration
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "your-webhook-secret")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "http://localhost:8000/webhook")
    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "1000"))
    
    def validate_settings(self):
        """Validate that all required settings are present"""
        errors = []
        
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if not self.BLAND_API_KEY:
            errors.append("BLAND_API_KEY is required")
            
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

# Create a single settings instance to be used throughout the app
settings = Settings()

# Validate settings on import
try:
    settings.validate_settings()
    print("INFO: Settings loaded and validated successfully.")
except ValueError as e:
    print(f"FATAL ERROR: {e}")
    raise