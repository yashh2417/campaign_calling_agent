from fastapi import APIRouter, Body, HTTPException, Response
from services import features_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/features", tags=["Features"])

@router.post("/test-voice")
def test_voice_endpoint(
    voice: str = Body(..., embed=True),
    user_phone_number: str = Body(..., embed=True)
):
    """
    Make an actual test call to the user's phone number to preview a voice.
    Uses /v1/calls endpoint to make real phone calls.
    """
    logger.info(f"📞 Voice test call request: {user_phone_number} with voice '{voice}'")
    
    # Validate inputs
    if not user_phone_number or not voice:
        raise HTTPException(status_code=400, detail="Phone number and voice are required")
    
    # Basic phone number validation
    if not user_phone_number.startswith('+'):
        raise HTTPException(status_code=400, detail="Phone number must start with + (international format)")
    
    return features_service.test_agent_voice(user_phone_number=user_phone_number, voice=voice)

@router.post("/generate-audio")
def generate_voice_audio_endpoint(
    text: str = Body(..., embed=True),
    voice: str = Body(..., embed=True)
):
    """
    Generate audio file using the /v1/speak endpoint.
    This creates an audio file that can be played in the browser.
    """
    logger.info(f"🎵 Audio generation request with voice '{voice}'")
    
    if not text or not voice:
        raise HTTPException(status_code=400, detail="Text and voice are required")
    
    if len(text) > 1000:
        raise HTTPException(status_code=400, detail="Text must be less than 1000 characters")
    
    result = features_service.generate_voice_audio(text=text, voice=voice)
    
    # Return the audio file directly
    return Response(
        content=result["audio_data"],
        media_type=result["content_type"],
        headers={
            "Content-Disposition": f"attachment; filename=voice_{voice}.wav",
            "Content-Length": str(result["size_bytes"])
        }
    )

@router.get("/calls/{call_id}/recording")
def get_recording_endpoint(call_id: str):
    """
    Get the recording for a completed call.
    Uses /v1/recordings/{call_id} endpoint.
    """
    if not call_id:
        raise HTTPException(status_code=400, detail="Call ID is required")
    
    return features_service.get_call_recording_url(call_id=call_id)

@router.get("/available-voices")
def get_available_voices():
    """
    Get list of available voices for testing.
    """
    voices = [
        {"id": "maya", "name": "Maya", "gender": "female", "description": "Professional Female"},
        {"id": "ryan", "name": "Ryan", "gender": "male", "description": "Friendly Male"},
        {"id": "sophia", "name": "Sophia", "gender": "female", "description": "Warm Female"},
        {"id": "james", "name": "James", "gender": "male", "description": "Deep Male"},
        {"id": "maeve", "name": "Maeve", "gender": "female", "description": "Energetic Female"},
        {"id": "liam", "name": "Liam", "gender": "male", "description": "Calm Male"},
        {"id": "nat", "name": "Nat", "gender": "female", "description": "Natural Female"},
        {"id": "alex", "name": "Alex", "gender": "male", "description": "Clear Male"},
        {"id": "emily", "name": "Emily", "gender": "female", "description": "Cheerful Female"},
        {"id": "david", "name": "David", "gender": "male", "description": "Professional Male"}
    ]
    return {"success": True, "voices": voices}

@router.get("/test-connection")
def test_bland_api_connection():
    """
    Test Bland AI API connectivity.
    """
    try:
        # Simple test by generating a short audio clip
        result = features_service.generate_voice_audio("Test", "maya")
        return {
            "status": "success",
            "message": "Bland AI API connection successful",
            "api_working": True,
            "test_audio_size": result["size_bytes"]
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"API connection failed: {str(e)}",
            "api_working": False
        }