import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """
    Holds all the application settings, loaded from environment variables.
    """
    # API key for the Bland AI service
    BLAND_API_KEY: str = os.getenv("BLAND_API_KEY")
    
    # Database connection URL from Supabase or another provider
    DB_URL: str = os.getenv("DB_URL")
    
    # List of allowed origins for CORS, comma-separated
    ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    
    # --- NEW: API key for Google Gemini ---
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")

# Create a single settings instance to be used throughout the app
settings = Settings()
