#!/usr/bin/env python3
"""
Smart Weather Display Manager for Waveshare E-ink Display
Handles weather data fetching, calendar integration, and display formatting
"""

import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
import schedule

# Configuration
@dataclass
class DisplayConfig:
    """Configuration settings for the display"""
    width: int = 600
    height: int = 448
    refresh_interval: int = 1800  # 30 minutes
    weather_api_interval: int = 900  # 15 minutes
    location: Dict[str, float] = None
    timezone: str = "America/Denver"
    temperature_unit: str = "fahrenheit"
    max_events_today: int = 4
    max_events_daily: int = 3
    sleep_hours: Dict[str, int] = None
    
    def __post_init__(self):
        if self.location is None:
            self.location = {"lat": 39.74, "lon": -104.99}  # Denver
        if self.sleep_hours is None:
            self.sleep_hours = {"start": 23, "end": 6}

@dataclass
class WeatherData:
    """Weather data structure"""
    current_temp: float
    condition: str
    condition_icon: str
    location: str
    datetime_str: str
    wind_speed: float
    wind_direction: str
    uv_index: float
    air_quality: int
    hourly_forecast: List[Dict]
    daily_forecast: List[Dict]
    pollen_data: Dict

@dataclass
class EventData:
    """Calendar event data structure"""
    time: str
    title: str
    location: str
    weather_temp: float
    weather_icon: str
    rain_chance: int
    is_outdoor: bool

class WeatherAPI:
    """Handles weather data fetching from Open-Meteo API"""
    
    def __init__(self, config: DisplayConfig):
        self.config = config
        self.base_url = "https://api.open-meteo.com/v1"
        self.air_quality_url = "https://air-quality-api.open-meteo.com/v1"
        
    def fetch_weather_data(self) -> WeatherData:
        """Fetch comprehensive weather data"""
        try:
            # Main weather data
            weather_params = {
                "latitude": self.config.location["lat"],
                "longitude": self.config.location["lon"],
                "current": [
                    "temperature_2m", "weather_code", "wind_speed_10m",
                    "wind_direction_10m", "uv_index"
                ],
                "hourly": [
                    "temperature_2m", "weather_code", "precipitation_probability",
                    "wind_speed_10m", "uv_index"
                ],
                "daily": [
                    "temperature_2m_max", "temperature_2m_min", "weather_code",
                    "precipitation_probability_max"
                ],
                "temperature_unit": "fahrenheit" if self.config.temperature_unit == "fahrenheit" else "celsius",
                "wind_speed_unit": "mph",
                "timezone": self.config.timezone,
                "forecast_days": 7
            }
            
            response = requests.get(f"{self.base_url}/forecast", params=weather_params)
            response.raise_for_status()
            weather_json = response.json()
            
            # Air quality data
            air_params = {
                "latitude": self.config.location["lat"],
                "longitude": self.config.location["lon"],
                "current": ["us_aqi", "pm2_5", "pm10"],
                "hourly": ["alder_pollen", "birch_pollen", "grass_pollen", "ragweed_pollen"]
            }
            
            air_response = requests.get(f"{self.air_quality_url}/air-quality", params=air_params)
            air_json = air_response.json() if air_response.status_code == 200 else {}
            
            return self._process_weather_data(weather_json, air_json)
            
        except Exception as e:
            logging.error(f"Error fetching weather data: {e}")
            return self._get_dummy_weather_data()
    
    def _process_weather_data(self, weather_json: Dict, air_json: Dict) -> WeatherData:
        """Process raw weather API response into structured data"""
        current = weather_json.get("current", {})
        hourly = weather_json.get("hourly", {})
        daily = weather_json.get("daily", {})
        
        # Current conditions
        current_temp = current.get("temperature_2m", 0)
        weather_code = current.get("weather_code", 0)
        condition, icon = self._get_weather_condition(weather_code)
        
        # Wind data
        wind_speed = current.get("wind_speed_10m", 0)
        wind_dir = self._get_wind_direction(current.get("wind_direction_10m", 0))
        
        # UV and air quality
        uv_index = current.get("uv_index", 0)
        air_quality = air_json.get("current", {}).get("us_aqi", 25)
        
        # Hourly forecast (next 24 hours)
        hourly_forecast = []
        for i in range(min(24, len(hourly.get("time", [])))):
            hourly_forecast.append({
                "time": hourly["time"][i],
                "temperature": hourly["temperature_2m"][i],
                "weather_code": hourly["weather_code"][i],
                "precipitation_probability": hourly["precipitation_probability"][i],
                "uv_index": hourly["uv_index"][i]
            })
        
        # Daily forecast (next 3 days)
        daily_forecast = []
        for i in range(min(3, len(daily.get("time", [])))):
            daily_forecast.append({
                "date": daily["time"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
                "weather_code": daily["weather_code"][i],
                "precipitation_probability": daily["precipitation_probability_max"][i]
            })
        
        # Pollen data
        pollen_data = self._process_pollen_data(air_json.get("hourly", {}))
        
        return WeatherData(
            current_temp=current_temp,
            condition=condition,
            condition_icon=icon,
            location="Denver, CO",  # Could be made dynamic
            datetime_str=datetime.now().strftime("%A, %B %d • %I:%M %p"),
            wind_speed=wind_speed,
            wind_direction=wind_dir,
            uv_index=uv_index,
            air_quality=air_quality,
            hourly_forecast=hourly_forecast,
            daily_forecast=daily_forecast,
            pollen_data=pollen_data
        )
    
    def _get_weather_condition(self, code: int) -> Tuple[str, str]:
        """Convert weather code to condition and icon"""
        weather_codes = {
            0: ("Clear", "☀"),
            1: ("Mostly Clear", "🌤"),
            2: ("Partly Cloudy", "⛅"),
            3: ("Overcast", "☁"),
            45: ("Foggy", "🌫"),
            48: ("Rime Fog", "🌫"),
            51: ("Light Drizzle", "🌦"),
            53: ("Drizzle", "🌦"),
            55: ("Heavy Drizzle", "🌦"),
            61: ("Light Rain", "🌧"),
            63: ("Rain", "🌧"),
            65: ("Heavy Rain", "🌧"),
            71: ("Light Snow", "❄"),
            73: ("Snow", "❄"),
            75: ("Heavy Snow", "❄"),
            95: ("Thunderstorm", "⛈"),
        }
        return weather_codes.get(code, ("Unknown", "❓"))
    
    def _get_wind_direction(self, degrees: float) -> str:
        """Convert wind direction degrees to compass direction"""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(degrees / 22.5) % 16
        return directions[index]
    
    def _process_pollen_data(self, hourly_pollen: Dict) -> Dict:
        """Process pollen data from air quality API"""
        if not hourly_pollen:
            return {"tree": 2, "grass": 5, "ragweed": 1}
        
        # Get current hour pollen levels
        current_hour = datetime.now().hour
        
        return {
            "tree": hourly_pollen.get("alder_pollen", [0] * 24)[current_hour] or 2,
            "grass": hourly_pollen.get("grass_pollen", [0] * 24)[current_hour] or 5,
            "ragweed": hourly_pollen.get("ragweed_pollen", [0] * 24)[current_hour] or 1
        }
    
    def _get_dummy_weather_data(self) -> WeatherData:
        """Return dummy data in case of API failure"""
        return WeatherData(
            current_temp=72.0,
            condition="Partly Cloudy",
            condition_icon="⛅",
            location="Denver, CO",
            datetime_str=datetime.now().strftime("%A, %B %d • %I:%M %p"),
            wind_speed=12.0,
            wind_direction="SW",
            uv_index=6.0,
            air_quality=25,
            hourly_forecast=[],
            daily_forecast=[],
            pollen_data={"tree": 2, "grass": 5, "ragweed": 1}
        )

class CalendarManager:
    """Handles calendar integration and event processing"""
    
    def __init__(self, config: DisplayConfig):
        self.config = config
        
    def fetch_events(self) -> List[EventData]:
        """Fetch calendar events - placeholder for actual calendar integration"""
        # This would integrate with Google Calendar API, CalDAV, or parse ICS files
        # For now, returning mock data that matches your design
        
        mock_events = [
            {
                "time": "3:00 PM",
                "title": "Team Meeting",
                "location": "Conference Room B",
                "is_outdoor": False
            },
            {
                "time": "5:30 PM", 
                "title": "Grocery Shopping",
                "location": "King Soopers",
                "is_outdoor": False
            },
            {
                "time": "7:00 PM",
                "title": "Dinner w/ Sarah",
                "location": "Outdoor Patio",
                "is_outdoor": True
            },
            {
                "time": "8:30 PM",
                "title": "Evening Walk",
                "location": "City Park",
                "is_outdoor": True
            }
        ]
        
        return [self._create_event_data(event) for event in mock_events[:self.config.max_events_today]]
    
    def _create_event_data(self, event_dict: Dict) -> EventData:
        """Create EventData object with weather integration"""
        # This would map event time to hourly weather forecast
        # For now, using mock weather data
        
        return EventData(
            time=event_dict["time"],
            title=event_dict["title"],
            location=event_dict["location"],
            weather_temp=75.0,  # Would be from hourly forecast
            weather_icon="⛅",
            rain_chance=15,
            is_outdoor=event_dict["is_outdoor"]
        )

class DisplayRenderer:
    """Handles image generation for the e-ink display"""
    
    def __init__(self, config: DisplayConfig):
        self.config = config
        self.width = config.width
        self.height = config.height
        
        # Try to load fonts, fall back to default if not available
        try:
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/arial.ttf", 10)
            self.font_normal = ImageFont.truetype("/usr/share/fonts/truetype/arial.ttf", 11)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/arial.ttf", 16)
            self.font_xlarge = ImageFont.truetype("/usr/share/fonts/truetype/arial.ttf", 24)
        except:
            # Fall back to default font
            self.font_small = ImageFont.load_default()
            self.font_normal = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_xlarge = ImageFont.load_default()
    
    def render_display(self, weather_data: WeatherData, events: List[EventData]) -> Image.Image:
        """Render the complete display layout"""
        # Create white background
        image = Image.new('1', (self.width, self.height), 1)  # 1-bit for e-ink
        draw = ImageDraw.Draw(image)
        
        # Render header (80px height)
        self._render_header(draw, weather_data)
        
        # Render left column (today's events)
        self._render_today_column(draw, weather_data, events)
        
        # Render right column (3-day forecast)
        self._render_forecast_column(draw, weather_data)
        
        return image
    
    def _render_header(self, draw: ImageDraw, weather_data: WeatherData):
        """Render the header section with current weather and metrics"""
        # Header background and border
        draw.rectangle([0, 0, self.width, 80], outline=0, width=2)
        draw.line([0, 78, self.width, 78], fill=0, width=2)
        
        # Current weather (left section)
        temp_text = f"{weather_data.current_temp:.0f}°F"
        draw.text((20, 15), temp_text, font=self.font_xlarge, fill=0)
        
        condition_text = f"{weather_data.condition_icon} {weather_data.condition} • {weather_data.location}"
        draw.text((20, 40), condition_text, font=self.font_normal, fill=0)
        
        draw.text((20, 55), weather_data.datetime_str, font=self.font_small, fill=0)
        
        # Metrics (right sections)
        metrics = [
            ("Wind", f"{weather_data.wind_speed:.0f}", f"mph {weather_data.wind_direction}"),
            ("UV Index", f"{weather_data.uv_index:.0f}", "High" if weather_data.uv_index > 6 else "Moderate"),
            ("Air Quality", f"{weather_data.air_quality:.0f}", "Good" if weather_data.air_quality < 50 else "Moderate")
        ]
        
        for i, (label, value, unit) in enumerate(metrics):
            x = 360 + (i * 80)
            self._render_metric_box(draw, x, 10, label, value, unit)
    
    def _render_metric_box(self, draw: ImageDraw, x: int, y: int, label: str, value: str, unit: str):
        """Render a metric box in the header"""
        box_width = 75
        box_height = 60
        
        # Box border
        draw.rectangle([x, y, x + box_width, y + box_height], outline=0, width=1)
        
        # Text
        draw.text((x + 5, y + 5), label, font=self.font_small, fill=0)
        draw.text((x + 10, y + 20), value, font=self.font_large, fill=0)
        draw.text((x + 5, y + 40), unit, font=self.font_small, fill=0)
    
    def _render_today_column(self, draw: ImageDraw, weather_data: WeatherData, events: List[EventData]):
        """Render today's events column"""
        # Column divider
        draw.line([300, 80, 300, self.height], fill=0, width=1)
        
        # Section title
        draw.text((15, 90), "Today's Events + Weather", font=self.font_normal, fill=0)
        draw.line([15, 105, 285, 105], fill=0, width=1)
        
        # Events
        y_pos = 115
        for event in events:
            self._render_event(draw, 15, y_pos, event)
            y_pos += 60
        
        # Health summary
        health_y = y_pos + 20
        draw.line([15, health_y, 285, health_y], fill=0, width=1)
        draw.text((15, health_y + 10), "Health Summary:", font=self.font_normal, fill=0)
        
        pollen_text = f"Tree Pollen: Low ({weather_data.pollen_data['tree']}) • Grass: Medium ({weather_data.pollen_data['grass']})"
        draw.text((15, health_y + 25), pollen_text, font=self.font_small, fill=0)
        
        uv_text = f"UV High until 6 PM • Air Quality Good"
        draw.text((15, health_y + 40), uv_text, font=self.font_small, fill=0)
    
    def _render_event(self, draw: ImageDraw, x: int, y: int, event: EventData):
        """Render a single event"""
        # Event box
        draw.rectangle([x, y, x + 270, y + 50], outline=0, width=1)
        
        # Time
        draw.text((x + 5, y + 10), event.time, font=self.font_normal, fill=0)
        
        # Event details
        draw.text((x + 70, y + 5), event.title, font=self.font_normal, fill=0)
        draw.text((x + 70, y + 20), event.location, font=self.font_small, fill=0)
        
        # Weather
        weather_text = f"{event.weather_temp:.0f}°F {event.weather_icon}"
        draw.text((x + 200, y + 5), weather_text, font=self.font_normal, fill=0)
        rain_text = f"{event.rain_chance}% rain"
        draw.text((x + 200, y + 20), rain_text, font=self.font_small, fill=0)
    
    def _render_forecast_column(self, draw: ImageDraw, weather_data: WeatherData):
        """Render 3-day forecast column"""
        # Section title
        draw.text((315, 90), "3-Day Events + Weather", font=self.font_normal, fill=0)
        draw.line([315, 105, 585, 105], fill=0, width=1)
        
        # Mock daily events and weather
        daily_data = [
            ("Wed\n29", "Doctor (10 AM)\nLunch Meeting (12:30)\nGym Session (6 PM)", "79°/55°\n☀ 10%"),
            ("Thu\n30", "Client Presentation (2 PM)\nHappy Hour (5:30 PM)", "75°/52°\n🌧 65%"),
            ("Fri\n1", "Trip Departure (4 PM)\nLight schedule", "71°/49°\n⛅ 30%")
        ]
        
        y_pos = 115
        for day, events_text, weather_text in daily_data:
            self._render_daily_forecast(draw, 315, y_pos, day, events_text, weather_text)
            y_pos += 70
        
        # Recommendations
        rec_y = y_pos + 20
        draw.line([315, rec_y, 585, rec_y], fill=0, width=1)
        draw.text((315, rec_y + 10), "Recommendations:", font=self.font_normal, fill=0)
        
        recommendations = [
            "• Outdoor dining tonight: watch for rain",
            "• Thursday: bring umbrella", 
            "• Weekend trip: good weather"
        ]
        
        for i, rec in enumerate(recommendations):
            draw.text((315, rec_y + 25 + (i * 15)), rec, font=self.font_small, fill=0)
    
    def _render_daily_forecast(self, draw: ImageDraw, x: int, y: int, day: str, events: str, weather: str):
        """Render a single day forecast"""
        # Day box
        draw.rectangle([x, y, x + 270, y + 60], outline=0, width=1)
        
        # Day
        draw.text((x + 5, y + 10), day, font=self.font_normal, fill=0)
        
        # Events
        draw.text((x + 55, y + 5), events, font=self.font_small, fill=0)
        
        # Weather
        draw.text((x + 200, y + 10), weather, font=self.font_small, fill=0)

class SmartDisplayManager:
    """Main display manager that coordinates all components"""
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.weather_api = WeatherAPI(self.config)
        self.calendar_manager = CalendarManager(self.config)
        self.renderer = DisplayRenderer(self.config)
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('display.log'),
                logging.StreamHandler()
            ]
        )
        
        # Cache for weather data
        self.weather_cache = None
        self.last_weather_update = None
        
    def _load_config(self, config_path: str) -> DisplayConfig:
        """Load configuration from file or create default"""
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
                return DisplayConfig(**config_dict)
        except FileNotFoundError:
            config = DisplayConfig()
            self._save_config(config, config_path)
            return config
    
    def _save_config(self, config: DisplayConfig, config_path: str):
        """Save configuration to file"""
        with open(config_path, 'w') as f:
            json.dump(config.__dict__, f, indent=2)
    
    def update_display(self):
        """Main update function - fetches data and renders display"""
        try:
            logging.info("Starting display update...")
            
            # Check if we need to update weather data
            now = datetime.now()
            if (self.last_weather_update is None or 
                now - self.last_weather_update > timedelta(seconds=self.config.weather_api_interval)):
                
                logging.info("Fetching fresh weather data...")
                self.weather_cache = self.weather_api.fetch_weather_data()
                self.last_weather_update = now
            
            # Fetch calendar events
            events = self.calendar_manager.fetch_events()
            
            # Render display
            image = self.renderer.render_display(self.weather_cache, events)
            
            # Save for testing (replace with actual e-ink display code)
            image.save('display_output.png')
            logging.info("Display updated successfully")
            
            # TODO: Send to actual Waveshare display
            # self._send_to_display(image)
            
        except Exception as e:
            logging.error(f"Error updating display: {e}")
    
    def _send_to_display(self, image: Image.Image):
        """Send image to Waveshare e-ink display"""
        # This would use the Waveshare library
        # Example:
        # import waveshare_epd
        # epd = waveshare_epd.epd7in5_V2()
        # epd.init()
        # epd.display(epd.getbuffer(image))
        # epd.sleep()
        pass
    
    def run_scheduler(self):
        """Run the display with scheduled updates"""
        logging.info("Starting Smart Display Manager...")
        
        # Schedule regular updates
        schedule.every(self.config.refresh_interval // 60).minutes.do(self.update_display)
        
        # Initial update
        self.update_display()
        
        # Main loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # Example usage
    display_manager = SmartDisplayManager()
    
    # For testing, just run a single update
    display_manager.update_display()
    
    # Uncomment to run with scheduler
    # display_manager.run_scheduler()