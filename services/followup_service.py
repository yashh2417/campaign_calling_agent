import time
import re
from datetime import datetime, timezone
from core.config import settings
from core.database import logger
from schemas.call_data_schemas import SendCallRequest
from services.call_creation_service import create_call

async def schedule_follow_up_call(phone_number: str, pathway_id: str, original_call_id: str, delay_seconds: int):
    """
    Waits for a specified duration (in seconds) and then places a follow-up call.
    """
    logger.info(f"⏰ Scheduling follow-up call to {phone_number} in {delay_seconds / 60:.1f} minutes for original call {original_call_id}.")
    time.sleep(delay_seconds)
    
    logger.info(f"📞 Placing scheduled follow-up call to {phone_number}.")
    follow_up_request = SendCallRequest(
        phone_number=phone_number,
        pathway_id=pathway_id,
        task=f"Follow-up call for original call ID: {original_call_id}. This call was scheduled based on the user's request.",
        webhook=f"{settings.ALLOWED_ORIGINS[0]}/bland/postcall" if settings.ALLOWED_ORIGINS else None
    )
    
    try:
        await create_call(follow_up_request)
    except Exception as e:
        logger.error(f"❌ Failed to place follow-up call to {phone_number}: {e}")

def parse_follow_up_time(time_string: str) -> int:
    """
    Parses a time string from the AI. It now prioritizes ISO 8601 format.
    If parsing fails, it falls back to simple relative times, then a default.
    """
    default_delay_seconds = 3600  # 1 hour default
    
    if not isinstance(time_string, str) or time_string.lower() == 'no':
        return default_delay_seconds

    # parse ISO 8601 timestamp first
    try:
        # Assuming the AI returns UTC time.
        target_time_utc = datetime.fromisoformat(time_string.strip())
        
        # If the datetime object is naive, assume it's UTC
        if target_time_utc.tzinfo is None:
            target_time_utc = target_time_utc.replace(tzinfo=timezone.utc)
            
        now_utc = datetime.now(timezone.utc)
        
        delay = (target_time_utc - now_utc).total_seconds()
        
        # Return the calculated delay, ensuring it's not in the past
        return max(0, int(delay))
    except (ValueError, TypeError):
        logger.info(f"Could not parse '{time_string}' as ISO timestamp. Trying relative time parsing.")

    # Fallback to simple relative time parsing
    time_string = time_string.lower().strip()
    if "tomorrow" in time_string: return 24 * 3600
    if match := re.search(r'(\d+)\s+hour', time_string): return int(match.group(1)) * 3600
    if match := re.search(r'(\d+)\s+minute', time_string): return int(match.group(1)) * 60
    
    logger.warning(f"⚠️ Could not parse follow-up time string '{time_string}'. Using default delay.")
    return default_delay_seconds
