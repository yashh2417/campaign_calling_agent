import google.generativeai as genai
from core.config import settings
from core.database import logger

# Configure the Google AI client with the API key from settings
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
else:
    logger.warning("⚠️ GOOGLE_API_KEY not found. Embedding generation will be disabled.")

def generate_embedding(text: str) -> list[float] | None:
    """
    Generates a vector embedding for the given text using Google Gemini's API.

    Args:
        text: The input string to embed.

    Returns:
        A list of floats representing the vector embedding, or None if an error occurs.
    """
    if not text or not settings.GOOGLE_API_KEY:
        logger.warning("⚠️ Text is empty or Google API key is not set. Skipping embedding.")
        return None
        
    try:
        # Use a standard Google embedding model.
        # The task_type is important for tailoring the embedding to your use case.
        result = genai.embed_content(
            model="models/embedding-001",
            content=text.strip(),
            task_type="RETRIEVAL_DOCUMENT"
        )
        return result['embedding']
    except Exception as e:
        logger.error(f"❌ Could not generate embedding from Google AI: {e}")
        return None