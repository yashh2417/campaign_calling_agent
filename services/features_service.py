import requests
from fastapi import HTTPException
from core.config import settings
from core.database import logger

def test_agent_voice(user_phone_number: str, voice: str):
    """
    Makes a test call to the user's phone number to preview an agent's voice.
    """
    try:
        url = "https://api.bland.ai/v1/speak"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "phone_number": user_phone_number,
            "text": "Hello, this is a preview of my voice. I hope you like how I sound!",
            "voice": voice,
            "wait_for_greeting": False
        }
        
        logger.info(f"🗣️ Sending test voice call to {user_phone_number} with voice '{voice}'")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        if response.text:
            return response.json()
        else:
            # If the request was successful but the body is empty, it means the 
            # test call was initiated. We return our own success message.
            return {"status": "success", "message": f"Test call initiated to {user_phone_number}."}
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP error during test call: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to make test call: {e.response.text}")
    except Exception as e:
        logger.error(f"❌ Unexpected error during test call: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

def get_call_recording_url(call_id: str):
    """
    Retrieves the recording data for a completed call.
    """
    try:
        url = f"https://api.bland.ai/v1/recordings/{call_id}"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}"}
        
        logger.info(f"🎙️ Fetching recording for call: {call_id}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP error fetching recording for {call_id}: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch recording: {e.response.text}")
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching recording for {call_id}: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")