"""
Validation functions for marketplace business rules.
Author: TJ
"""

from datetime import datetime, timedelta
import re
from django.core.exceptions import ValidationError


def validate_lead_time(fulfillment_date):
    """
    Validate that fulfillment date is at least 48 hours from now.
    
    Args:
        fulfillment_date (datetime): The requested fulfillment/delivery date
        
    Returns:
        bool: True if valid
        
    Raises:
        ValidationError: If fulfillment date is less than 48 hours away
    """
    if not isinstance(fulfillment_date, datetime):
        raise ValidationError("Fulfillment date must be a datetime object")
    
    # Calculate minimum allowed date (48 hours from now)
    min_date = datetime.now() + timedelta(hours=48)
    
    if fulfillment_date < min_date:
        hours_diff = (fulfillment_date - datetime.now()).total_seconds() / 3600
        raise ValidationError(
            f"Fulfillment date must be at least 48 hours from now. "
            f"Current date is only {hours_diff:.1f} hours away."
        )
    
    return True


def validate_uk_postcode(postcode):
    """
    Validate UK postcode format.
    
    Accepts formats like: BS1 5JG, BS15JG, SW1A 1AA, etc.
    
    Args:
        postcode (str): The postcode to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValidationError: If postcode format is invalid
    """
    if not postcode or not isinstance(postcode, str):
        raise ValidationError("Postcode must be a non-empty string")
    
    # UK postcode regex pattern
    # Matches: A9 9AA, A99 9AA, AA9 9AA, AA99 9AA, A9A 9AA, AA9A 9AA
    pattern = r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$'
    
    if not re.match(pattern, postcode.upper().strip()):
        raise ValidationError(
            f"Invalid UK postcode format: '{postcode}'. "
            f"Expected format: 'BS1 5JG' or 'SW1A 1AA'"
        )
    
    return True


def validate_product_data(price, stock_quantity):
    """
    Validate product form data.
    
    Args:
        price (Decimal/float): Product price
        stock_quantity (int): Available stock quantity
        
    Returns:
        bool: True if valid
        
    Raises:
        ValidationError: If price or stock quantity is invalid
    """
    errors = []
    
    # Validate price
    try:
        price_value = float(price)
        if price_value <= 0:
            errors.append("Price must be greater than 0")
    except (TypeError, ValueError):
        errors.append("Price must be a valid number")
    
    # Validate stock quantity
    try:
        stock_value = int(stock_quantity)
        if stock_value < 0:
            errors.append("Stock quantity cannot be negative")
    except (TypeError, ValueError):
        errors.append("Stock quantity must be a valid integer")
    
    if errors:
        raise ValidationError(errors)
    
    return True


def validate_status_transition(current_status, new_status):
    """
    Validate allowed order status transitions.
    
    Allowed transitions:
    - pending → confirmed, cancelled
    - confirmed → ready, cancelled
    - ready → delivered, cancelled
    - delivered → (terminal state, no transitions)
    - cancelled → (terminal state, no transitions)
    
    Args:
        current_status (str): Current order status
        new_status (str): Desired new status
        
    Returns:
        bool: True if transition is allowed
        
    Raises:
        ValidationError: If transition is not allowed
    """
    # Define allowed transitions
    allowed_transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['ready', 'cancelled'],
        'ready': ['delivered', 'cancelled'],
        'delivered': [],  # Terminal state
        'cancelled': [],  # Terminal state
    }
    
    # Validate current status exists
    if current_status not in allowed_transitions:
        raise ValidationError(f"Invalid current status: '{current_status}'")
    
    # Check if transition is allowed (or if we are just submitting the same status again)
    if new_status != current_status and new_status not in allowed_transitions.get(current_status, []):
        raise ValidationError(
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed_transitions[current_status]) or 'none (terminal state)'}"
        )
    
    return True

# Lines 152-228 by Alex McBride
def validate_content_moderation(text, field_name="Content"):
    """
    Validate user-generated content for inappropriate material.
    
    Checks for:
    - Prohibited words and phrases
    - Excessive repetition (spam patterns)
    - Suspicious link patterns
    
    Args:
        text (str): The content to validate
        field_name (str): Name of the field being validated (for error messages)
        
    Returns:
        bool: True if content is appropriate
        
    Raises:
        ValidationError: If content contains inappropriate material
    """
    if not text or not isinstance(text, str):
        return True
    
    text_lower = text.lower()
    
    # Not exhaustive, sample of common spam/inappropriate phrases
    prohibited_words = [
        'get rich quick', 'make money fast', 'click here now',
        'limited time offer only', 'buy now cheap', 'fuck', 'shit', 'bitch',
    ]
    
    # Check for prohibited words
    for word in prohibited_words:
        if word in text_lower:
            raise ValidationError(
                f"{field_name} contains inappropriate or prohibited content. "
                f"Please ensure your content is family-friendly and appropriate for all audiences."
            )
    
    # Check for excessive repetition (spam pattern)
    # Look for the same word repeated more than 10 times
    words = text_lower.split()
    word_count = {}
    for word in words:
        if len(word) >= 3:  # Check words 3 characters or longer
            word_count[word] = word_count.get(word, 0) + 1
            if word_count[word] > 10:
                raise ValidationError(
                    f"{field_name} appears to contain spam (excessive word repetition). "
                    f"Please write natural, meaningful content."
                )
    
    # Check for excessive URL patterns (more than 5 links is suspicious)
    url_patterns = ['http://', 'https://', 'www.', '.com', '.net', '.org']
    url_count = sum(1 for pattern in url_patterns if pattern in text_lower)
    if url_count > 5:
        raise ValidationError(
            f"{field_name} contains too many links. "
            f"Please limit external links and focus on your content."
        )
    
    # Check for excessive capitalisation
    if len(text) > 20:
        uppercase_ratio = sum(1 for c in text if c.isupper()) / len(text)
        if uppercase_ratio > 0.7:
            raise ValidationError(
                f"{field_name} contains excessive capitalisation. "
                f"Please use normal sentence case."
            )
    
    # Check minimum content length for meaningful posts
    if len(text.strip()) < 10:
        raise ValidationError(
            f"{field_name} is too short. Please provide more detailed information."
        )
    
    return True
