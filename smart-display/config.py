"""Configuration settings for the smart display"""
import os
from pathlib import Path

# Display settings
DISPLAY_WIDTH = 600
DISPLAY_HEIGHT = 448
UPDATE_INTERVAL = 30  # minutes

# API Keys (use environment variables for security)
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

# Location settings
LOCATION_PARAMS = {
    'postalcode' : '80204',
    'country' : 'US'
}

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
