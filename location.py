"""
Location detection module for Talenta API
Uses IP-based geolocation with fallback to configured coordinates
"""

import requests
from typing import Dict, Optional


def detect_location() -> Dict[str, str]:
    """
    Detect user's current location using IP-based geolocation

    Returns:
        Dictionary with latitude and longitude as strings

    Raises:
        Exception: If location detection fails
    """
    try:
        print('🌍 Detecting your location...')

        # Use ip-api.com for free IP geolocation (no API key required)
        url = 'https://ip-api.com/json/?fields=lat,lon,city,country,status,message'

        response = requests.get(url, timeout=10)
        response.raise_for_status()

        result = response.json()

        if result.get('status') == 'fail':
            raise Exception(result.get('message', 'IP geolocation service error'))

        lat = result.get('lat')
        lon = result.get('lon')

        if not lat or not lon:
            raise Exception('Location coordinates not available')

        city = result.get('city', 'Unknown')
        country = result.get('country', 'Unknown')

        print(f"✅ Location detected: {lat}, {lon} ({city}, {country})")

        return {
            'latitude': str(lat),
            'longitude': str(lon)
        }

    except requests.exceptions.Timeout:
        raise Exception('Location detection timeout')
    except requests.exceptions.RequestException as error:
        raise Exception(f'Network request failed: {error}')
    except Exception as error:
        print(f"⚠️  Location detection failed: {error}")
        raise


def get_location(config: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Get location with fallback to config values

    Args:
        config: Configuration dictionary with fallback lat/long

    Returns:
        Dictionary with latitude and longitude as strings

    Raises:
        Exception: If detection fails and no fallback is available
    """
    try:
        # Try to detect location automatically
        detected_location = detect_location()
        return detected_location
    except Exception as error:
        # Fallback to config values
        if config and config.get('latitude') and config.get('longitude'):
            print('📍 Using configured location as fallback')
            return {
                'latitude': config['latitude'],
                'longitude': config['longitude']
            }
        else:
            raise Exception('Unable to detect location and no fallback coordinates provided in config')


if __name__ == '__main__':
    # Example usage
    try:
        location = get_location()
        print(f"Location: {location}")
    except Exception as e:
        print(f"Error: {e}")
