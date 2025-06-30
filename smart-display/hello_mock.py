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
        """Return demo weather data (no API calls)"""
        logging.info("Using demo weather data (no API calls)")
        return self._get_demo_weather_data()
    
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
        """Convert weather code to condition and ASCII-safe icon"""
        weather_codes = {
            0: ("Clear", "SUN"),
            1: ("Mostly Clear", "SUN"),
            2: ("Partly Cloudy", "P.CLD"),
            3: ("Overcast", "CLOUD"),
            45: ("Foggy", "FOG"),
            48: ("Rime Fog", "FOG"),
            51: ("Light Drizzle", "DRZL"),
            53: ("Drizzle", "DRZL"),
            55: ("Heavy Drizzle", "DRZL"),
            61: ("Light Rain", "RAIN"),
            63: ("Rain", "RAIN"),
            65: ("Heavy Rain", "RAIN"),
            71: ("Light Snow", "SNOW"),
            73: ("Snow", "SNOW"),
            75: ("Heavy Snow", "SNOW"),
            95: ("Thunderstorm", "STORM"),
        }
        return weather_codes.get(code, ("Unknown", "?"))
    
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
    
    def _get_demo_weather_data(self) -> WeatherData:
        """Return comprehensive demo data that matches the mockup exactly"""
        # Create realistic hourly forecast for today
        current_hour = datetime.now().hour
        hourly_forecast = []
        
        # Generate hourly data for next 24 hours
        base_temps = [76, 75, 73, 70, 68, 65, 63, 61, 59, 58, 60, 65, 70, 75, 78, 79, 77, 75, 72, 70, 68, 66, 64, 62]
        rain_chances = [15, 30, 35, 25, 20, 10, 5, 5, 5, 10, 15, 20, 25, 30, 25, 20, 15, 10, 8, 5, 3, 5, 8, 12]
        weather_codes = [2, 2, 3, 3, 1, 1, 0, 0, 0, 1, 2, 2, 2, 3, 3, 2, 2, 2, 1, 1, 0, 0, 1, 1]
        
        for i in range(24):
            hour_time = (datetime.now() + timedelta(hours=i)).strftime("%Y-%m-%dT%H:00")
            hourly_forecast.append({
                "time": hour_time,
                "temperature": base_temps[i],
                "weather_code": weather_codes[i],
                "precipitation_probability": rain_chances[i],
                "uv_index": max(0, 8 - abs(i - 12) * 0.8) if 6 <= (current_hour + i) % 24 <= 18 else 0
            })
        
        # Create 3-day forecast
        daily_forecast = [
            {
                "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "temp_max": 79,
                "temp_min": 55,
                "weather_code": 0,  # Clear
                "precipitation_probability": 10
            },
            {
                "date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
                "temp_max": 75,
                "temp_min": 52,
                "weather_code": 63,  # Rain
                "precipitation_probability": 65
            },
            {
                "date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                "temp_max": 71,
                "temp_min": 49,
                "weather_code": 2,  # Partly Cloudy
                "precipitation_probability": 30
            }
        ]
        
        return WeatherData(
            current_temp=72.0,
            condition="Partly Cloudy",
            condition_icon="P.CLD",
            location="Denver, CO",
            datetime_str=datetime.now().strftime("%A, %B %d • %I:%M %p"),
            wind_speed=12.0,
            wind_direction="SW",
            uv_index=6.0,
            air_quality=25,
            hourly_forecast=hourly_forecast,
            daily_forecast=daily_forecast,
            pollen_data={"tree": 2, "grass": 5, "ragweed": 1}
        )

class CalendarManager:
    """Handles calendar integration and event processing"""
    
    def __init__(self, config: DisplayConfig):
        self.config = config
        
    def fetch_events(self) -> List[EventData]:
        """Return demo calendar events with realistic weather integration"""
        
        # Demo events that match the mockup exactly
        demo_events = [
            {
                "time": "3:00 PM",
                "title": "Team Meeting",
                "location": "Conference Room B",
                "is_outdoor": False,
                "temp": 76,
                "icon": "P.CLD",
                "rain": 15
            },
            {
                "time": "5:30 PM", 
                "title": "Grocery Shopping",
                "location": "King Soopers",
                "is_outdoor": False,
                "temp": 75,
                "icon": "SUN",
                "rain": 30
            },
            {
                "time": "7:00 PM",
                "title": "Dinner w/ Sarah",
                "location": "Outdoor Patio",
                "is_outdoor": True,
                "temp": 73,
                "icon": "CLOUD",
                "rain": 35
            },
            {
                "time": "8:30 PM",
                "title": "Evening Walk",
                "location": "City Park",
                "is_outdoor": True,
                "temp": 70,
                "icon": "P.CLD",
                "rain": 25
            }
        ]
        
        return [self._create_demo_event_data(event) for event in demo_events[:self.config.max_events_today]]
    
    def _create_demo_event_data(self, event_dict: Dict) -> EventData:
        """Create EventData object with pre-defined demo weather"""
        
        return EventData(
            time=event_dict["time"],
            title=event_dict["title"],
            location=event_dict["location"],
            weather_temp=event_dict["temp"],
            weather_icon=event_dict["icon"],
            rain_chance=event_dict["rain"],
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
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
            self.font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.font_xlarge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            try:
                # Try alternative font paths
                self.font_small = ImageFont.truetype("arial.ttf", 10)
                self.font_normal = ImageFont.truetype("arial.ttf", 11)
                self.font_large = ImageFont.truetype("arial.ttf", 16)
                self.font_xlarge = ImageFont.truetype("arial.ttf", 24)
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
        temp_text = f"{weather_data.current_temp:.0f}F"
        draw.text((20, 15), temp_text, font=self.font_xlarge, fill=0)
        
        condition_text = f"{weather_data.condition_icon} {weather_data.condition} - {weather_data.location}"
        draw.text((20, 40), condition_text, font=self.font_normal, fill=0)
        
        draw.text((20, 55), weather_data.datetime_str.replace("•", "-"), font=self.font_small, fill=0)
        
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
        
        pollen_text = f"Tree Pollen: Low ({weather_data.pollen_data['tree']}) - Grass: Medium ({weather_data.pollen_data['grass']})"
        draw.text((15, health_y + 25), pollen_text, font=self.font_small, fill=0)
        
        uv_text = f"UV High until 6 PM - Air Quality Good"
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
        weather_text = f"{event.weather_temp:.0f}F {event.weather_icon}"
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
            ("Wed\n29", "Doctor (10 AM)\nLunch Meeting (12:30)\nGym Session (6 PM)", "79/55F\nSUN 10%"),
            ("Thu\n30", "Client Presentation (2 PM)\nHappy Hour (5:30 PM)", "75/52F\nRAIN 65%"),
            ("Fri\n1", "Trip Departure (4 PM)\nLight schedule", "71/49F\nP.CLD 30%")
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
            "- Outdoor dining tonight: watch for rain",
            "- Thursday: bring umbrella", 
            "- Weekend trip: good weather"
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
    
    def update_display_with_time(self):
        """Update display with current time (for demo purposes)"""
        try:
            logging.info("Quick time update...")
            
            # Use cached weather data, just update time
            if self.weather_cache:
                # Update the datetime string
                self.weather_cache.datetime_str = datetime.now().strftime("%A, %B %d - %I:%M %p")
            
            # Get events (they're demo data, so always the same)
            events = self.calendar_manager.fetch_events()
            
            # Render display
            weather_data = self.weather_cache or self.weather_api.fetch_weather_data()
            image = self.renderer.render_display(weather_data, events)
            
            # Save with timestamp for demo purposes
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f'display_output_{timestamp}.png'
            image.save(filename)
            
            # Also save as main file
            image.save('display_output.png')
            logging.info(f"Display updated - saved as {filename}")
            
        except Exception as e:
            logging.error(f"Error in time update: {e}")
    
    def update_display(self):
        """Main update function - fetches data and renders display"""
        try:
            logging.info("Starting full display update...")
            
            # Check if we need to update weather data
            now = datetime.now()
            if (self.last_weather_update is None or 
                now - self.last_weather_update > timedelta(seconds=self.config.weather_api_interval)):
                
                logging.info("Fetching fresh weather data...")
                self.weather_cache = self.weather_api.fetch_weather_data()
                self.last_weather_update = now
            else:
                logging.info("Using cached weather data...")
            
            # Fetch calendar events
            events = self.calendar_manager.fetch_events()
            
            # Render display
            image = self.renderer.render_display(self.weather_cache, events)
            
            # Save for testing (replace with actual e-ink display code)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'display_full_{timestamp}.png'
            image.save(filename)
            image.save('display_output.png')
            
            logging.info(f"Full display update completed - saved as {filename}")
            
            # TODO: Send to actual Waveshare display
            # self._send_to_display(image)
            
        except Exception as e:
            logging.error(f"Error updating display: {e}")
            raise
    
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
        logging.info(f"Refresh interval: {self.config.refresh_interval // 60} minutes")
        
        # Schedule regular updates (convert seconds to minutes)
        update_minutes = max(1, self.config.refresh_interval // 60)
        schedule.every(update_minutes).minutes.do(self.update_display)
        
        # For demo purposes, also update every 30 seconds to see changes
        schedule.every(30).seconds.do(self.update_display_with_time)
        
        # Initial update
        logging.info("Performing initial display update...")
        self.update_display()
        
        # Main loop
        logging.info("Starting refresh loop...")
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)  # Check every second for more responsive scheduling
        except KeyboardInterrupt:
            logging.info("Shutdown requested by user")
            raise

if __name__ == "__main__":
    import sys
    
    # Create display manager
    display_manager = SmartDisplayManager()
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
        print("Starting continuous refresh mode...")
        print("Press Ctrl+C to stop")
        try:
            display_manager.run_scheduler()
        except KeyboardInterrupt:
            print("\nDisplay manager stopped.")
    else:
        print("Running single update (demo mode)...")
        print("Use --continuous flag for automatic refresh")
        display_manager.update_display()
        print("Demo complete! Check 'display_output.png' for results.")
        print("For continuous mode, run: python display_manager.py --continuous")