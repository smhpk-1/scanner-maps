"""
API Key validator for Google Places API.
"""

import requests
from typing import Tuple


class PlacesAPIValidator:
    """Validates Google Places API keys by making test API calls."""

    # Google Places API endpoints
    PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self):
        """Initialize the validator."""
        pass

    def validate_key(self, api_key: str) -> Tuple[str, str]:
        """
        Validate a Google Places API key by making a test request.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple of (status, error_message)
            Status can be: 'valid', 'invalid', 'rate_limited', 'restricted', 'error'
        """
        try:
            # Try Places API Nearby Search with a known location (New York City)
            params = {
                "key": api_key,
                "location": "40.7128,-74.0060",  # NYC coordinates
                "radius": 100,
                "type": "restaurant"
            }
            
            response = requests.get(
                self.PLACES_NEARBY_URL,
                params=params,
                timeout=10
            )
            
            data = response.json()
            status = data.get("status", "")
            
            if status == "OK" or status == "ZERO_RESULTS":
                # Key is valid (ZERO_RESULTS still means the key works)
                return ("valid", None)
            
            elif status == "REQUEST_DENIED":
                error_msg = data.get("error_message", "Request denied")
                
                # Check if it's a restriction issue
                if "API key" in error_msg.lower() and "restricted" in error_msg.lower():
                    return ("restricted", error_msg)
                elif "not authorized" in error_msg.lower():
                    return ("restricted", error_msg)
                else:
                    return ("invalid", error_msg)
            
            elif status == "OVER_QUERY_LIMIT":
                return ("rate_limited", "Over query limit")
            
            elif status == "INVALID_REQUEST":
                # Try geocoding as fallback to check if key works for other APIs
                return self._try_geocoding(api_key)
            
            else:
                return ("error", f"Unknown status: {status}")

        except requests.exceptions.Timeout:
            return ("error", "Request timeout")
        except requests.exceptions.RequestException as e:
            return ("error", f"Request failed: {str(e)}")
        except Exception as e:
            return ("error", f"Unexpected error: {str(e)}")

    def _try_geocoding(self, api_key: str) -> Tuple[str, str]:
        """
        Fallback validation using Geocoding API.
        
        Some keys might be restricted to specific APIs, so we try
        multiple endpoints.
        """
        try:
            params = {
                "key": api_key,
                "address": "1600 Amphitheatre Parkway, Mountain View, CA"
            }
            
            response = requests.get(
                self.GEOCODING_URL,
                params=params,
                timeout=10
            )
            
            data = response.json()
            status = data.get("status", "")
            
            if status == "OK":
                return ("valid", "Works with Geocoding API")
            elif status == "REQUEST_DENIED":
                return ("invalid", data.get("error_message", "Request denied"))
            elif status == "OVER_QUERY_LIMIT":
                return ("rate_limited", "Over query limit")
            else:
                return ("invalid", f"Status: {status}")
                
        except Exception as e:
            return ("error", f"Geocoding fallback failed: {str(e)}")

    def get_key_info(self, api_key: str) -> dict:
        """
        Get detailed information about a valid API key.
        
        Returns dict with available services and quota info.
        """
        info = {
            "places_api": False,
            "geocoding_api": False,
            "details": {}
        }
        
        # Check Places API
        status, _ = self.validate_key(api_key)
        if status == "valid":
            info["places_api"] = True
        
        # Check Geocoding API
        status, _ = self._try_geocoding(api_key)
        if status == "valid":
            info["geocoding_api"] = True
        
        return info
