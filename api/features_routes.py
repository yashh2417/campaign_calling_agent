from fastapi import APIRouter, Body
from services import features_service

router = APIRouter(prefix="/api/features", tags=["Features"])

@router.post("/test-voice")
def test_voice_endpoint(
    voice: str = Body(..., embed=True),
    user_phone_number: str = Body(..., embed=True)
):
    """
    Endpoint to make a test call to the user's phone number to preview a voice.
    """
    return features_service.test_agent_voice(user_phone_number=user_phone_number, voice=voice)

@router.get("/calls/{call_id}/recording")
def get_recording_endpoint(call_id: str):
    """
    Endpoint to get the recording URL for a completed call.
    """
    return features_service.get_call_recording_url(call_id=call_id)