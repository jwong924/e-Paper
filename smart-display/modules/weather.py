"""Weather data fetching and processing"""
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
import config

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self, api_key: str = None, city: str = None):
        self.api_key = api_key or config.WEATHER_API_KEY
        self.city = city or config.CITY
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.cache_file = config.CACHE_DIR / 'weather_cache.json'
        
        # Create cache directory if it doesn't exist
        config.CACHE_DIR.mkdir(exist_ok=True)
    
    def get_current_weather(self) -> Optional[Dict]:
        """Fetch current weather data"""
        # Check cache first
        cached_data = self._get_cached_data()
        if cached_data:
            logger.info("Using cached weather data")
            return cached_data
        
        try:
            url = f"{self.base_url}/weather"
            params = {
                'q': self.city,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            logger.info(f"Fetching weather data for {self.city}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Process and cache the data
            processed_data = self._process_weather_data(data)
            self._cache_data(processed_data)
            
            return processed_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Weather API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Weather API response parsing failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching weather: {e}")
            return None
    
    def get_forecast(self, days: int = 3) -> Optional[Dict]:
        """Fetch weather forecast"""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'q': self.city,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': days * 8  # 8 forecasts per day (3-hour intervals)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._process_forecast_data(data)
            
        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            return None
    
    def _process_weather_data(self, raw_data: Dict) -> Dict:
        """Process raw weather data into display format"""
        try:
            return {
                'temperature': round(raw_data['main']['temp']),
                'feels_like': round(raw_data['main']['feels_like']),
                'humidity': raw_data['main']['humidity'],
                'pressure': raw_data['main']['pressure'],
                'description': raw_data['weather'][0]['description'].title(),
                'icon': raw_data['weather'][0]['icon'],
                'wind_speed': raw_data.get('wind', {}).get('speed', 0),
                'wind_direction': raw_data.get('wind', {}).get('deg', 0),
                'city': raw_data['name'],
                'country': raw_data['sys']['country'],
                'timestamp': datetime.now().isoformat()
            }
        except KeyError as e:
            logger.error(f"Missing key in weather data: {e}")
            return {}
    
    def _process_forecast_data(self, raw_data: Dict) -> Dict:
        """Process raw forecast data"""
        try:
            forecasts = []
            for item in raw_data['list'][:24]:  # Next 24 3-hour periods
                forecasts.append({
                    'datetime': datetime.fromisoformat(item['dt_txt']),
                    'temperature': round(item['main']['temp']),
                    'description': item['weather'][0]['description'].title(),
                    'icon': item['weather'][0]['icon']
                })
            
            return {
                'city': raw_data['city']['name'],
                'forecasts': forecasts,
                'timestamp': datetime.now().isoformat()
            }
        except KeyError as e:
            logger.error(f"Missing key in forecast data: {e}")
            return {}
    
    def _get_cached_data(self) -> Optional[Dict]:
        """Get cached weather data if still valid"""
        try:
            if not self.cache_file.exists():
                return None
            
            with open(self.cache_file, 'r') as f:
                cached = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cache_time < timedelta(minutes=config.CACHE_DURATION):
                return cached
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading weather cache: {e}")
            return None
    
    def _cache_data(self, data: Dict):
        """Cache weather data"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error caching weather data: {e}")