import os
import google.generativeai as genai
from core.database import logger

# Configure the Gemini API key
try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    logger.error("❌ GEMINI_API_KEY environment variable not set.")
    # You might want to handle this more gracefully, e.g., by raising an exception
    # or having a fallback mechanism.
    
# Create the Generative Model instance
model = genai.GenerativeModel('gemini-2.0-flash')

def get_sentiment_from_transcript(transcript: str) -> str:
    """
    Analyzes the sentiment of a transcript using the Gemini LLM.

    Args:
        transcript: The text of the call transcript.

    Returns:
        A string representing the sentiment (e.g., "positive", "negative", "neutral").
    """
    if not transcript or not transcript.strip():
        return "unknown"
        
    try:
        # Simple and effective prompt for sentiment analysis
        prompt = f"""
        Analyze the sentiment of the following call transcript. 
        Classify it as 'positive', 'negative', or 'neutral'.
        Return only the single word for the classification.

        Transcript:
        ---
        {transcript}
        ---

        Sentiment:
        """
        
        response = model.generate_content(prompt)
        
        sentiment = response.text.strip().lower()
        
        # Basic validation to ensure the output is one of the expected values
        if sentiment not in ["positive", "negative", "neutral"]:
            logger.warning(f"⚠️ Unexpected sentiment value from Gemini: {sentiment}")
            return "unknown" # Fallback for unexpected responses
            
        logger.info(f"🧠 Gemini sentiment analysis for transcript: '{sentiment}'")
        return sentiment
        
    except Exception as e:
        logger.error(f"❌ Error during Gemini sentiment analysis: {e}", exc_info=True)
        return "unknown" # Fallback in case of an API error