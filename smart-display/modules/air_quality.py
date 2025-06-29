import json
import requests
import logging
import os
import sys
import pytz
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Import the geocoding function (assuming it's in a file called geocoding.py)
from location_coordinates import get_location_data

# Constants
OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
logger = logging.getLogger(__name__)


def save_air_quality_cache(air_quality, cache_file):
    """Save weather cache data to file."""
    try:
        with open(cache_file, 'w') as f:
            json.dump(air_quality, f, indent=3)
        logger.info(f"Weather cache saved to {cache_file}")
    except IOError as e:
        logger.error(f"Could not save weather cache file: {e}")


def get_air_quality_data(location_data):    
    if not location_data.get('lat') and location_data.get('lon'):
        raise ValueError("Could not get location coordinates")
    
    # Extract latitude and longitude
    lat = location_data.get('lat')
    lon = location_data.get('lon')
    
    if not lat or not lon:
        raise ValueError("Invalid coordinates received from geocoding")
    
    logger.info(f"Location: {location_data.get('display_name', 'Unknown')}")
    logger.info(f"Coordinates: {lat}, {lon}")
    
    # Prepare Open-Meteo API parameters
    # Freedom Units
    air_quality_params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'us_aqi,alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen',
        'hourly': 'alder_pollen,birch_pollen,grass_pollen,mugwort_pollen,olive_pollen,ragweed_pollen,pm2_5,pm10',
        'timezone': 'auto',
        'forecast_days': 3
    }
    
    logger.info("Making Open-Meteo API request...")
    
    try:
        response = requests.get(OPEN_METEO_URL, params=air_quality_params, timeout=10)
        response.raise_for_status()
        
        # Log response for debugging
        logger.info(f"Air Quality API Response Status: {response.status_code}")
        logger.info(f"Air Quality API Response Content Length: {len(response.text)}")
        logger.debug(f"Air Quality API Response Content: {response.text}")
        
        # Parse response
        air_quality_data = response.json()
        
        # Add location info to weather data for context
        air_quality_data['location_name'] = location_data.get('display_name')
        
        # Save to cache
        save_air_quality_cache(air_quality_data, 'air_quality_cache_raw.json')
        
        logger.info("Air Quality data retrieved and cached successfully")
        return air_quality_data
        
    except requests.RequestException as e:
        logger.error(f"Error making Air Quality API request: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Air Quality API response: {e}")
        raise

def format_air_quality_data(air_quality_data):
    hourly_data = air_quality_data.get('hourly', {})
    daily_data = air_quality_data.get('daily', {})
    current_data = air_quality_data.get('current', {})
    temperature_unit = air_quality_data.get("temperature_unit")[0]
    wind_speed_unit = air_quality_data.get("wind_speed_unit")[0]
    precipitation_unit = air_quality_data.get("precipitation_unit")[0]

    # Format Current Data
    logging.info(f"Formatting current data")
    current_dt = datetime.fromisoformat(current_data.get('time'))
    formatted_current_data = {
        "datetime": current_data.get('time'),
        "date": current_dt.date().strftime("%Y-%m-%d"),
        "time": current_dt.time().strftime("%H:%M"),
        "day": current_dt.strftime("%A"),
        "temperature": current_data.get('temperature'),
        "wind_speed": current_data.get('windspeed'),
        "precipitation": current_data.get('precipitation')
    }

    # Format Hourly Data
    logging.info(f"Formatting hourly data")
    formatted_hourly_data = []
    i = 0
    for index, datetime_str in enumerate(hourly_data.get('time', [])):
        if i > 3:
            break
        hourly_dt = datetime.fromisoformat(datetime_str)
        if hourly_dt > current_dt + timedelta(minutes=25):
            hour_data = {
                "datetime": datetime_str,
                "date": hourly_dt.date().strftime("%Y-%m-%d"),
                "time": hourly_dt.time().strftime("%H:%M"),
                "day": hourly_dt.strftime("%A"),
                "apparent_temperature": hourly_data.get('apparent_temperature', [])[index],
                "cloud_cover": hourly_data.get('cloud_cover', [])[index],
                "wind_speed": hourly_data.get('wind_speed_10m', [])[index],
                "precipitation_probability": hourly_data.get('precipitation_probability', [])[index],
                "precipitation": hourly_data.get('precipitation', [])[index],
                "snowfall": hourly_data.get('snowfall', [])[index],
                "snow_depth": hourly_data.get('snow_depth', [])[index],
                "visibility": hourly_data.get('visibility', [])[index],
                "uv_index": hourly_data.get('uv_index', [])[index]
            }
            formatted_hourly_data.append(hour_data)
            i += 1
        else:
            logging.info(f"Skipping hourly data: {datetime_str} because it's in the past")
            pass



    # Format Daily Data
    logging.info(f"Formatting daily data")
    formatted_daily_data = []
    for index, datetime_str in enumerate(daily_data.get('time', [])):
        daily_dt = datetime.fromisoformat(datetime_str)
        day_data = {
            "datetime": datetime_str,
            "date": daily_dt.date().strftime("%Y-%m-%d"),
            "day": daily_dt.strftime("%A"),
            "apparent_temperature_max": daily_data.get('apparent_temperature_max')[index],
            "apparent_temperature_min": daily_data.get('apparent_temperature_min')[index],
            "apparent_temperature_mean": daily_data.get('apparent_temperature_mean')[index],
            "precipitation_sum": daily_data.get('precipitation_sum')[index],
            "snowfall_sum": daily_data.get('snowfall_sum')[index],
            "precipitation_hours": daily_data.get('precipitation_hours')[index],
            "precipitation_probability_mean": daily_data.get('precipitation_probability_mean')[index],
            "weather_code": daily_data.get('weather_code')[index],
            "sunrise": daily_data.get('sunrise')[index],
            "sunset": daily_data.get('sunset')[index],
            "uv_index_max": daily_data.get('uv_index_max')[index]
        }
        formatted_daily_data.append(day_data)

    # Final Format of Cache
    formatted_weather_data = {
        "timestamp": datetime.now().isoformat(),
        "location": air_quality_data.get('location_name'),
        "timezone": air_quality_data.get('timezone'),
        "meta":{
            "coordinates": f"{air_quality_data.get('latitude', 'N/A')}, {air_quality_data.get('longitude', 'N/A')}",
            "temperature_unit": temperature_unit,
            "wind_speed_unit": wind_speed_unit,
            "precipitation_unit": precipitation_unit
        },
        "current": {
            "data": formatted_current_data,
            "units": air_quality_data.get('current_weather_units', {})
        },
        "hourly": {
            "data": formatted_hourly_data,
            "units": air_quality_data.get('hourly_units', {})
        },
        "daily": {
            "data": formatted_daily_data,
            "units": air_quality_data.get('daily_units', {})
        }
    }
    
    return formatted_weather_data

def main():
    """Main function for standalone execution"""
    try:
        # First, get location coordinates
        logger.info("Getting location coordinates...")
        location_data = get_location_data()

        # Start Weather Retrieval
        logger.info("Starting weather data retrieval...")
        air_quality_data = get_air_quality_data(location_data)
        formatted_air_quality_data = format_air_quality_data(air_quality_data)

        if formatted_air_quality_data:
            # Print formatted summary
            save_air_quality_cache(formatted_air_quality_data, 'air_quality_cache_formatted.json')
            logging.info(f"Formatted air quality data saved to: air_quality_cache_formatted.json")
            print("=" * 60)
            print("Formatted weather data saved to: weather_cache_formatted.json")
            print("=" * 60)
            
        else:
            print("No weather data found")
            
    except Exception as e:
        logger.error(f"Error getting weather data: {e}")
        print(f"Error: {e}")

# For standalone execution
if __name__ == "__main__":
    main()