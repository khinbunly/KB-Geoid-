"""Input validation and sanitization helpers."""

from typing import Tuple
from app.config import settings


class ValidationError(ValueError):
    """Custom exception for user input validation errors."""
    pass


def validate_coordinates(lat: float, lon: float) -> Tuple[float, float]:
    """
    Validate latitude and longitude ranges.
    
    Latitude: [-90.0, 90.0]
    Longitude: [-180.0, 180.0]
    """
    if not (-90.0 <= lat <= 90.0):
        raise ValidationError(
            f"Invalid Latitude `{lat}`. Must be between -90.0° and +90.0°."
        )
    
    if not (-180.0 <= lon <= 180.0):
        # Also handle 0..360 longitude
        if 0.0 <= lon <= 360.0:
            lon = ((lon + 180.0) % 360.0) - 180.0
        else:
            raise ValidationError(
                f"Invalid Longitude `{lon}`. Must be between -180.0° and +180.0°."
            )
            
    return lat, lon


def validate_height(height: float) -> float:
    """Validate height within terrestrial limits [-500m to 10,000m]."""
    if not (-500.0 <= height <= 10000.0):
        raise ValidationError(
            f"Height value `{height}m` is outside reasonable terrestrial limits (-500m to 10,000m)."
        )
    return height


def validate_file_size(size_bytes: int) -> None:
    """Validate file upload size against max configured limit."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError(
            f"File size ({size_bytes / (1024*1024):.1f} MB) exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )
