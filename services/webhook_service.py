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
    
    # Application settings
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = int(os.getenv("DEFAULT_PAGE_SIZE", "50"))
    MAX_PAGE_SIZE: int = int(os.getenv("MAX_PAGE_SIZE", "1000"))
    
    @property
    def WEBHOOK_URL(self) -> str:
        """Get webhook URL with proper validation and cleanup"""
        webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8000/webhook")
        
        # Clean up common issues
        # Remove double slashes (except after http://)
        if "//" in webhook_url.replace("https://", "").replace("http://", ""):
            # Split at protocol, clean the rest, rejoin
            if webhook_url.startswith("https://"):
                clean_url = "https://" + webhook_url[8:].replace("//", "/")
            elif webhook_url.startswith("http://"):
                clean_url = "http://" + webhook_url[7:].replace("//", "/")
            else:
                clean_url = webhook_url.replace("//", "/")
            
            print(f"INFO: Cleaned webhook URL from '{webhook_url}' to '{clean_url}'")
            return clean_url
        
        return webhook_url
    
    def validate_settings(self):
        """Validate that all required settings are present"""
        errors = []
        
        if not self.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        if not self.BLAND_API_KEY:
            errors.append("BLAND_API_KEY is required")
        
        # Validate webhook URL format
        webhook_url = self.WEBHOOK_URL
        if not webhook_url.startswith(("http://", "https://")):
            errors.append("WEBHOOK_URL must start with http:// or https://")
        
        if "localhost" in webhook_url or "127.0.0.1" in webhook_url:
            print("WARNING: Using localhost webhook URL - this won't work in production")
            
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

# Create a single settings instance to be used throughout the app
settings = Settings()

# Validate settings on import
try:
    settings.validate_settings()
    print("INFO: Settings loaded and validated successfully.")
    print(f"INFO: Using webhook URL: {settings.WEBHOOK_URL}")
except ValueError as e:
    print(f"FATAL ERROR: {e}")
    raise