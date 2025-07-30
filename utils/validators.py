import re

def validate_phone_number(phone_number: str) -> bool:
    """
    Validates a phone number using a simple regex.
    Ensures it follows a basic international format.
    """
    if not phone_number:
        return False
    # This regex matches a plus sign, followed by 1-14 digits.
    if re.match(r'^\+?[1-9]\d{1,14}$', phone_number):
        return True
    return False