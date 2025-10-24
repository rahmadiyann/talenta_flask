"""
Location detection module for Talenta API
Uses IP-based geolocation with fallback to configured coordinates
"""

from typing import Dict, Optional
from src.core.logger import setup_logger

logger = setup_logger("talenta_location_setup")

def get_location(config: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Get location with from config values
    """
    return {
        'latitude': config['latitude'],
        'longitude': config['longitude']
    }


if __name__ == '__main__':
    # Example usage
    try:
        location = get_location()
        logger.info(f"Location: {location}")
    except Exception as e:
        logger.error(f"Error: {e}")
