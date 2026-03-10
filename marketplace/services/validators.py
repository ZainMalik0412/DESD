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
    - pending → accepted, cancelled
    - placed → paid, cancelled
    - paid → fulfilled, cancelled
    - fulfilled → (terminal state, no transitions)
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
        'placed': ['paid', 'cancelled'],
        'paid': ['fulfilled', 'cancelled'],
        'fulfilled': [],  # Terminal state
        'cancelled': [],  # Terminal state
    }
    
    # Validate current status exists
    if current_status not in allowed_transitions:
        raise ValidationError(f"Invalid current status: '{current_status}'")
    
    # Check if transition is allowed
    if new_status not in allowed_transitions.get(current_status, []):
        raise ValidationError(
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(allowed_transitions[current_status]) or 'none (terminal state)'}"
        )
    
    return True
