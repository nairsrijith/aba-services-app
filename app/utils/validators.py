import re
from wtforms.validators import ValidationError

def validate_phone_number(form, field):
    """
    Validates phone number format:
    - Exactly 10 digits
    - Can contain optional spaces, dashes, or parentheses
    - Must be a valid North American format
    """
    # Remove all non-digit characters
    phone = re.sub(r'\D', '', field.data)
    
    if not phone:
        raise ValidationError('Phone number is required')
    
    if len(phone) != 10:
        raise ValidationError('Phone number must be exactly 10 digits')
    
    # Check if it's a valid North American format
    if not re.match(r'^[2-9]\d{9}$', phone):
        raise ValidationError('Invalid phone number format')