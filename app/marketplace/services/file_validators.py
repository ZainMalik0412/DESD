"""
Image file validation functions for product uploads.
Ensures uploaded images meet security and quality requirements.
"""

import os
from django.core.exceptions import ValidationError


def validate_image_file_extension(value):
    """
    Validate that uploaded file has an allowed image extension.
    
    Args:
        value: The uploaded file object
        
    Raises:
        ValidationError: If file extension is not allowed
    """
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    ext = os.path.splitext(value.name)[1].lower()
    
    if ext not in allowed_extensions:
        raise ValidationError(
            f"File extension '{ext}' is not allowed. "
            f"Allowed extensions: {', '.join(allowed_extensions)}"
        )


def validate_image_file_size(value):
    """
    Validate that uploaded image is not too large.
    Maximum size: 5MB
    
    Args:
        value: The uploaded file object
        
    Raises:
        ValidationError: If file size exceeds limit
    """
    max_size_mb = 5
    max_size_bytes = max_size_mb * 1024 * 1024  # 5MB in bytes
    
    if value.size > max_size_bytes:
        raise ValidationError(
            f"Image file size ({value.size / 1024 / 1024:.2f} MB) exceeds "
            f"maximum allowed size of {max_size_mb} MB"
        )


def validate_image_content_type(value):
    """
    Validate that uploaded file has an allowed content type.
    
    Args:
        value: The uploaded file object
        
    Raises:
        ValidationError: If content type is not allowed
    """
    allowed_types = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp'
    ]
    
    # Get content type from the file
    content_type = getattr(value, 'content_type', None)
    
    if content_type and content_type not in allowed_types:
        raise ValidationError(
            f"File content type '{content_type}' is not allowed. "
            f"Allowed types: {', '.join(allowed_types)}"
        )
