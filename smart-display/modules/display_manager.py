"""E-paper display management"""
import sys
import logging
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List, Optional
from datetime import datetime
import config

# Add waveshare library path
sys.path.append('/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib')

try:
    from waveshare_epd import epd5in83
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    logging.warning("Waveshare EPD library not found. Display will be simulated.")

logger = logging.getLogger(__name__)

class DisplayManager:
    def __init__(self):
        self.width = config.DISPLAY_WIDTH
        self.height = config.DISPLAY_HEIGHT
        self.fonts = self._load_fonts()
        
        if DISPLAY_AVAILABLE:
            self.epd = epd5in83.EPD()
        else:
            self.epd = None
    
    def _load_fonts(self) -> Dict:
        """Load fonts for display"""
        fonts = {}
        for size_name, size_value in config.FONT_SIZES.items():
            try:
                font_path = config.FONTS[size_name]
                fonts[size_name] = ImageFont.truetype(font_path, size_value)
            except OSError:
                logger.warning(f"Could not load font {font_path}, using default")
                fonts[size_name] = ImageFont.load_default()
        
        return fonts
    
    def initialize(self):
        """Initialize the e-paper display"""
        if self.epd:
            logger.info("Initializing e-paper display...")
            self.epd.init()
            self.epd.Clear()
        else:
            logger.info("Display simulation mode")
    
    def create_layout(self, weather_data: Dict, events: List[Dict], 
                     news_headlines: List[str] = None) -> Image.Image:
        """Create the main display layout"""
        # Create white background
        image = Image.new('L', (self.width, self.height), 255)
        draw = ImageDraw.Draw(image)
        
        y_pos = 10
        
        # Header with current time
        y_pos = self._draw_header(draw, y_pos)
        
        # Weather section
        if weather_data:
            y_pos = self._draw_weather_section(draw, weather_data, y_pos)
        
        # Events section
        if events:
            y_pos = self._draw_events_section(draw, events, y_pos)
        
        # News section (if available)
        if news_headlines and y_pos < self.height - 100:
            y_pos = self._draw_news_section(draw, news_headlines, y_pos)
        
        return image
    
    def _draw_header(self, draw: ImageDraw.Draw, y_pos: int) -> int:
        """Draw header with current time and date"""
        current_time = datetime.now().strftime("%A, %B %d, %Y")
        current_clock = datetime.now().strftime("%H:%M")
        
        # Date
        draw.text((10, y_pos), current_time, font=self.fonts['medium'], fill=0)
        
        # Time (right aligned)
        clock_bbox = draw.textbbox((0, 0), current_clock, font=self.fonts['large'])
        clock_width = clock_bbox[2] - clock_bbox[0]
        draw.text((self.width - clock_width - 10, y_pos), current_clock, 
                 font=self.fonts['large'], fill=0)
        
        y_pos += 40
        
        # Separator line
        draw.line([(10, y_pos), (self.width - 10, y_pos)], fill=0, width=2)
        
        return y_pos + 20
    
    def _draw_weather_section(self, draw: ImageDraw.Draw, weather_data: Dict, y_pos: int) -> int:
        """Draw weather information"""
        # Section title
        draw.text((10, y_pos), "WEATHER", font=self.fonts['large'], fill=0)
        y_pos += 35
        
        # Temperature (large, prominent)
        temp_text = f"{weather_data.get('temperature', 'N/A')}°C"
        draw.text((10, y_pos), temp_text, font=self.fonts['large'], fill=0)
        
        # Condition next to temperature
        condition = weather_data.get('description', 'Unknown')
        temp_bbox = draw.textbbox((0, 0), temp_text, font=self.fonts['large'])
        draw.text((temp_bbox[2] + 20, y_pos + 5), condition, 
                 font=self.fonts['medium'], fill=0)
        
        y_pos += 35
        
        # Additional weather info
        humidity = weather_data.get('humidity', 'N/A')
        feels_like = weather_data.get('feels_like', 'N/A')
        
        draw.text((10, y_pos), f"Feels like {feels_like}°C", 
                 font=self.fonts['small'], fill=0)
        draw.text((200, y_pos), f"Humidity {humidity}%", 
                 font=self.fonts['small'], fill=0)
        
        return y_pos + 40
    
    def _draw_events_section(self, draw: ImageDraw.Draw, events: List[Dict], y_pos: int) -> int:
        """Draw upcoming events"""
        draw.text((10, y_pos), "UPCOMING EVENTS", font=self.fonts['large'], fill=0)
        y_pos += 35
        
        if not events:
            draw.text((10, y_pos), "No upcoming events", font=self.fonts['medium'], fill=0)
            return y_pos + 30
        
        for event in events[:4]:  # Max 4 events
            # Event title
            draw.text((10, y_pos), f"• {event['title']}", font=self.fonts['medium'], fill=0)
            y_pos += 22
            
            # Event time and location
            time_location = event['time_display']
            if event.get('location'):
                time_location += f" • {event['location']}"
            
            draw.text((20, y_pos), time_location, font=self.fonts['small'], fill=0)
            y_pos += 25
        
        return y_pos
    
    def _draw_news_section(self, draw: ImageDraw.Draw, headlines: List[str], y_pos: int) -> int:
        """Draw news headlines"""
        draw.text((10, y_pos), "NEWS", font=self.fonts['large'], fill=0)
        y_pos += 35
        
        for headline in headlines[:3]:  # Max 3 headlines
            # Truncate long headlines
            truncated = headline[:80] + "..." if len(headline) > 80 else headline
            draw.text((10, y_pos), f"• {truncated}", font=self.fonts['small'], fill=0)
            y_pos += 20
        
        return y_pos
    
    def display_image(self, image: Image.Image):
        """Display image on e-paper"""
        if self.epd:
            logger.info("Updating e-paper display...")
            self.epd.display(self.epd.getbuffer(image))
        else:
            # Save image for debugging when display not available
            image.save('/tmp/smart_display_output.png')
            logger.info("Display image saved to /tmp/smart_display_output.png")
    
    def sleep(self):
        """Put display to sleep"""
        if self.epd:
            self.epd.sleep()