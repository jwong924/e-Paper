"""Configuration settings for the smart display"""
import os
from pathlib import Path

# Display settings
DISPLAY_WIDTH = 600
DISPLAY_HEIGHT = 448
UPDATE_INTERVAL = 30  # minutes

# API Keys (use environment variables for security)
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', 'your_api_key_here')
NEWS_API_KEY = os.getenv('NEWS_API_KEY', 'your_news_api_key_here')

# Location settings
CITY = os.getenv('DISPLAY_CITY', 'London')
COUNTRY_CODE = os.getenv('COUNTRY_CODE', 'GB')

# Font paths
FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
FONTS = {
    'large': str(FONT_DIR / 'DejaVuSans-Bold.ttf'),
    'medium': str(FONT_DIR / 'DejaVuSans.ttf'),
    'small': str(FONT_DIR / 'DejaVuSans.ttf'),
}

FONT_SIZES = {
    'large': 24,
    'medium': 18,
    'small': 14,
}

# Logging settings
LOG_LEVEL = 'INFO'
LOG_FILE = '/var/log/smart_display.log'

# Cache settings
CACHE_DIR = Path.home() / '.smart_display_cache'
CACHE_DURATION = 10  # minutes