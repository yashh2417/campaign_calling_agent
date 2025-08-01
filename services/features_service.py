import requests
from fastapi import HTTPException
from core.config import settings
from core.database import logger

def test_agent_voice(user_phone_number: str, voice: str):
    """
    Makes an actual test call to the user's phone number to preview a voice.
    Uses /v1/calls endpoint to make real phone calls.
    """
    try:
        # Use /v1/calls endpoint for actual phone calls
        url = "https://api.bland.ai/v1/calls"
        headers = {
            "Authorization": f"Bearer {settings.BLAND_API_KEY}", 
            "Content-Type": "application/json"
        }
        
        # Payload for making actual phone calls
        payload = {
            "phone_number": user_phone_number,
            "task": f"Hello! This is a voice preview call using the {voice} voice. I'm calling to let you test how this AI agent sounds. This is just a quick test call to demonstrate the voice quality. Thank you for trying out our AI calling system!",
            "voice": voice,
            "max_duration": 2,  # Keep test calls short (2 minutes max)
            "record": False,    # Don't record test calls
            "wait_for_greeting": True,  # Wait for user to answer
            "language": "en"
        }
        
        logger.info(f"📞 Making actual test call to {user_phone_number} with voice '{voice}'")
        logger.info(f"🔑 API Key present: {bool(settings.BLAND_API_KEY)}")
        logger.info(f"🌐 Endpoint: {url}")
        logger.info(f"📤 Payload: {payload}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        logger.info(f"📥 Status Code: {response.status_code}")
        logger.info(f"📥 Content-Type: {response.headers.get('content-type', 'unknown')}")
        logger.info(f"📥 Content-Length: {len(response.content)}")
        
        # Log response safely
        try:
            response_text = response.text
            if len(response_text) > 500:
                response_preview = response_text[:500] + "... (truncated)"
            else:
                response_preview = response_text
            logger.info(f"📥 Response: {repr(response_preview)}")
        except UnicodeDecodeError:
            logger.warning("📥 Response contains binary data")
        
        # Check if response is successful
        if response.status_code in [200, 201]:
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type:
                try:
                    result = response.json()
                    call_id = result.get('call_id')
                    logger.info(f"✅ Test call initiated successfully! Call ID: {call_id}")
                    return {
                        "status": "success",
                        "message": f"Test call initiated to {user_phone_number}. You should receive a call shortly!",
                        "voice": voice,
                        "call_id": call_id,
                        "call_data": result
                    }
                except ValueError as json_error:
                    logger.warning(f"⚠️ Response is not valid JSON: {json_error}")
                    return {
                        "status": "success",
                        "message": f"Test call initiated to {user_phone_number}. You should receive a call shortly!",
                        "voice": voice,
                        "note": "Call initiated but response format unexpected"
                    }
            else:
                # Non-JSON response but successful
                logger.info("✅ Test call initiated (non-JSON response)")
                return {
                    "status": "success",
                    "message": f"Test call initiated to {user_phone_number}. You should receive a call shortly!",
                    "voice": voice
                }
        
        else:
            # Handle error responses
            error_msg = f"HTTP {response.status_code}"
            try:
                if 'application/json' in response.headers.get('content-type', ''):
                    error_data = response.json()
                    error_msg = error_data.get('message', error_data.get('error', error_msg))
                elif response.text and len(response.text) < 1000:
                    error_msg = response.text
            except:
                pass
            
            logger.error(f"❌ Test call failed: {error_msg}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Test call failed: {error_msg}"
            )
            
    except requests.exceptions.Timeout:
        logger.error("❌ Request timeout during test call")
        raise HTTPException(
            status_code=504, 
            detail="Test call request timed out - please try again"
        )
    except requests.exceptions.ConnectionError:
        logger.error("❌ Connection error during test call")
        raise HTTPException(
            status_code=502, 
            detail="Could not connect to calling service - please check your internet connection"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during test call: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Test call failed: {str(e)}"
        )

def generate_voice_audio(text: str, voice: str):
    """
    Generate audio file using the /v1/speak endpoint.
    This creates an audio file, not a phone call.
    """
    try:
        url = "https://api.bland.ai/v1/speak"
        headers = {
            "Authorization": f"Bearer {settings.BLAND_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "voice": voice
        }
        
        logger.info(f"🎵 Generating audio with voice '{voice}'")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # Return the audio file
            return {
                "status": "success",
                "content_type": response.headers.get('content-type'),
                "audio_data": response.content,
                "size_bytes": len(response.content)
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Audio generation failed: HTTP {response.status_code}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def get_call_recording_url(call_id: str):
    """
    Retrieves the recording for a completed call.
    Uses the /v1/recordings/{call_id} endpoint.
    """
    try:
        url = f"https://api.bland.ai/v1/recordings/{call_id}"
        headers = {"Authorization": f"Bearer {settings.BLAND_API_KEY}"}
        
        logger.info(f"🎙️ Fetching recording for call: {call_id}")
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            try:
                recording_data = response.json()
                return {
                    "status": "success",
                    "call_id": call_id,
                    "recording_data": recording_data
                }
            except ValueError:
                logger.warning("⚠️ Recording response is not JSON")
                return {
                    "status": "success",
                    "call_id": call_id,
                    "message": "Recording found but format unexpected",
                    "raw_response": response.text[:500]
                }
        elif response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Recording not found for call {call_id}"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch recording: HTTP {response.status_code}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching recording for {call_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))