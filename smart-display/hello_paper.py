#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import time
from PIL import Image, ImageDraw, ImageFont

path = '/home/pi/e-Paper/RaspberryPi_JetsonNano/python/lib'

if os.path.exists(path):
    sys.path.append(path)

# Import the Waveshare library for 5.83inch display
from waveshare_epd import epd5in83_V2 as epd5in83

def main():
    try:
        print("Initializing E-Paper Display...")
        
        # Initialize the display
        epd = epd5in83.EPD()
        epd.init()
        
        # Get display dimensions
        width = epd.width    # 648
        height = epd.height  # 480
        
        print(f"Display size: {width} x {height}")
        
        # Clear the display (optional - removes any previous content)
        print("Clearing display...")
        epd.Clear()
        
        # Create a new image with white background
        image = Image.new('1', (width, height), 255)  # '1' for 1-bit pixels, 255 for white
        draw = ImageDraw.Draw(image)
        
        # Try to load a font (falls back to default if not available)
        try:
            # You can adjust the font size
            font_large = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 36)
            font_medium = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
            font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
        except:
            print("Custom fonts not found, using default font")
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw text on the image
        draw.text((50, 50), "Hello MarQ!", font=font_large, fill=0)  # 0 for black
        draw.text((50, 170), "Run by Jon", font=font_small, fill=0)
        
        # Draw some shapes for demonstration
        draw.rectangle([(50, 220), (598, 280)], outline=0, width=2)
        draw.text((60, 235), "I'll put shit somewhere", font=font_small, fill=0)
        
        # Draw a circle
        draw.ellipse([(400, 300), (500, 400)], outline=0, width=3)
        draw.text((350, 420), "Circle", font=font_small, fill=0)
        
        # Add timestamp
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        draw.text((50, 450), f"Updated: {current_time}", font=font_small, fill=0)
        
        # Display the image on e-Paper
        print("Updating display...")
        epd.display(epd.getbuffer(image))
        
        print("Display updated successfully!")
        print("The display will remain showing this content even when powered off.")
        
        # Put the display to sleep to save power
        epd.sleep()
        
    except IOError as e:
        print(f"IOError: {e}")
        print("Please check your wiring and SPI configuration")
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Make sure you have the correct Waveshare library files")

if __name__ == '__main__':
    main()