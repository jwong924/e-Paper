import json
import requests
import logging
import os
import sys
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

CACHE_FILE = "location_coordinates_cache.json"
url = "https://nominatim.openstreetmap.org/search"
headers = {
    'User-Agent' : 'smart-display/1.0'  
}
logger = logging.getLogger(__name__)

def load_cache():
    """Load existing cache data from file if it exists, create empty cache if not."""
    if os.path.exists(CACHE_FILE):
        logger.info(f"Cache file {CACHE_FILE} exists")
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
            logger.info(f"Cache file {CACHE_FILE} loaded")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load cache file: {e}")
            return {}
    else:
        # Create empty cache file if it doesn't exist
        logger.info(f"Cache file {CACHE_FILE} does not exist, creating new one")
        empty_cache = {}
        save_cache(empty_cache)
        return empty_cache

def save_cache(cache_data):
    """Save cache data to file."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        logger.info(f"Cache saved to {CACHE_FILE}")
    except IOError as e:
        logger.error(f"Could not save cache file: {e}")

def create_cache_key(params):
    """Create a unique key for caching based on country + location."""
    country = params.get('country', '')
    
    if 'postalcode' in params:
        location = params['postalcode']
        logger.info(f"Cache key: {country}_{location}")
        return f"{country}_{location}"
    elif 'city' in params:
        location = params['city']
        logger.info(f"Cache key: {country}_{location}")
        return f"{country}_{location}"
    else:
        logger.error("Cache key requires either postalcode or city")
        raise ValueError("Cache key requires either postalcode or city")

def get_location_data(location_params=None):
    # Use provided params or fall back to config
    if location_params is None:
        params = config.LOCATION_PARAMS.copy()
    else:
        params = location_params.copy()
    
    # Add required API parameters
    params.update({
        'format': 'jsonv2',
        'limit': 1
    })
    
    # Load existing cache
    cache = load_cache()
    cache_key = create_cache_key(params)
    
    # Check if data exists in cache
    if cache_key in cache:
        logger.info("Data found in cache, using cached result")
        return cache[cache_key][0]  # Return first result
    else:
        logger.info("Data not in cache, making API request")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Log response for debugging
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Content Length: {len(response.text)}")
        logger.debug(f"Response Content: {response.text}")
       
        # Parse response
        data = response.json()
        
        if not data:
            logger.warning("No data returned from geocoding API")
            return None
       
        # Save to cache
        cache[cache_key] = data
        save_cache(cache)
        
        return data[0]  # Return first result

def main():
    """Main function for standalone execution"""
    try:
        result = get_location_data()
        if result:
            print(json.dumps(result, indent=2))
        else:
            logger.error("No location data found")
    except Exception as e:
        logger.error(f"Error getting location data: {e}")

# For standalone execution
if __name__ == "__main__":
    main()