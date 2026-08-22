#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iran Mountain Weather Bot
ربات پیش‌بینی آب و هوای قله‌های پرتردد ایران

This bot fetches weather forecasts from Open-Meteo API
and sends them to a Telegram group.
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ============================================
# Configuration
# ============================================

# Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Open-Meteo API
OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'

# Weather codes (WMO)
WEATHER_CODES = {
    0: '☀️ صاف',
    1: '🌤️ تقریباً صاف',
    2: '⛅ نیمه‌ابری',
    3: '☁️ ابری',
    45: '🌫️ مه',
    48: '🌫️ مه یخی',
    51: '🌦️ نم‌نم باران خفیف',
    53: '🌦️ نم‌نم باران',
    55: '🌦️ نم‌نم باران شدید',
    56: '🌧️ نم‌نم باران یخی',
    57: '🌧️ نم‌نم باران یخی شدید',
    61: '🌧️ باران خفیف',
    63: '🌧️ باران',
    65: '🌧️ باران شدید',
    66: '🌧️ باران یخی خفیف',
    67: '🌧️ باران یخی شدید',
    71: '❄️ برف خفیف',
    73: '❄️ برف',
    75: '❄️ برف شدید',
    77: '❄️ دانه‌های برف',
    80: '🌧️ رگبار باران',
    81: '🌧️ رگبار باران متوسط',
    82: '🌧️ رگبار باران شدید',
    85: '🌨️ رگبار برف',
    86: '🌨️ رگبار برف شدید',
    95: '⛈️ طوفان',
    96: '⛈️ طوفان با تگرگ',
    99: '⛈️ طوفان شدید با تگرگ',
}


# ============================================
# Load mountains data
# ============================================

def load_mountains():
    """Load mountains data from JSON file"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    mountains_file = os.path.join(script_dir, 'mountains.json')
    
    with open(mountains_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data['mountains']


# ============================================
# Weather API
# ============================================

def get_weather_forecast(mountain, forecast_days=3):
    """Get weather forecast from Open-Meteo API"""
    
    params = {
        'latitude': mountain['latitude'],
        'longitude': mountain['longitude'],
        'elevation': mountain['elevation'],
        'daily': ','.join([
            'temperature_2m_max',
            'temperature_2m_min',
            'precipitation_sum',
            'snowfall_sum',
            'wind_speed_10m_max',
            'wind_gusts_10m_max',
            'weathercode'
        ]),
        'timezone': 'Asia/Tehran',
        'forecast_days': forecast_days
    }
    
    url = f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"Error fetching weather for {mountain['name']}: {e}")
        return None


# ============================================
# Format message
# ============================================

def format_weather_message(mountain, weather_data):
    """Format weather data into a Telegram message"""
    
    if not weather_data or 'daily' not in weather_data:
        return None
    
    daily = weather_data['daily']
    
    # Get tomorrow and day after tomorrow
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    
    msg = f"🏔️ **{mountain['name']}** ({mountain['name_en']})\n"
    msg += f"📏 ارتفاع: {mountain['elevation']:,} متر\n"
    msg += f"📍 {mountain['province']} | {mountain['range']}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    for i in range(min(2, len(daily['time']))):
        date_str = daily['time'][i]
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        if i == 0:
            day_name = "📍 فردا"
        else:
            day_name = "📍 پس‌فردا"
        
        weather_code = daily['weathercode'][i]
        weather_desc = WEATHER_CODES.get(weather_code, f'کد {weather_code}')
        
        temp_max = daily['temperature_2m_max'][i]
        temp_min = daily['temperature_2m_min'][i]
        precipitation = daily['precipitation_sum'][i]
        snowfall = daily['snowfall_sum'][i]
        wind_speed = daily['wind_speed_10m_max'][i]
        wind_gusts = daily['wind_gusts_10m_max'][i]
        
        msg += f"\n📅 **{day_name}** ({date_str})\n"
        msg += f"🌤️ {weather_desc}\n"
        msg += f"🌡️ دما: {temp_min}° تا {temp_max}°\n"
        
        if precipitation > 0:
            msg += f"🌧️ بارش: {precipitation} میلی‌متر\n"
        
        if snowfall > 0:
            msg += f"❄️ برف: {snowfall} سانتی‌متر\n"
        
        msg += f"💨 باد: {wind_speed} km/h"
        
        if wind_gusts > wind_speed * 1.5:
            msg += f" (تندباد: {wind_gusts} km/h)"
        
        msg += "\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🌐 Open-Meteo API | @iran_mountain_weather"
    
    return msg


# ============================================
# Telegram API
# ============================================

def send_telegram_message(text, parse_mode='Markdown'):
    """Send message to Telegram"""
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        print("Message preview:")
        print(text)
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text,
        'parse_mode': parse_mode
    }
    
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            
            if result.get('ok'):
                print(f"✅ Message sent successfully")
                return True
            else:
                print(f"❌ Error: {result.get('description', 'Unknown error')}")
                return False
                
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False


# ============================================
# Main
# ============================================

def main():
    """Main function"""
    
    print("=" * 50)
    print("🏔️ Iran Mountain Weather Bot")
    print("=" * 50)
    
    # Load mountains
    mountains = load_mountains()
    print(f"\n📋 Loaded {len(mountains)} mountains")
    
    # Get forecast for each mountain
    messages = []
    
    for i, mountain in enumerate(mountains, 1):
        print(f"\n[{i}/{len(mountains)}] Fetching weather for {mountain['name']}...")
        
        weather_data = get_weather_forecast(mountain)
        
        if weather_data:
            message = format_weather_message(mountain, weather_data)
            if message:
                messages.append(message)
                print(f"  ✅ Weather data received")
            else:
                print(f"  ❌ Failed to format message")
        else:
            print(f"  ❌ Failed to fetch weather data")
    
    # Send messages
    print(f"\n📤 Sending {len(messages)} messages to Telegram...")
    
    for i, message in enumerate(messages, 1):
        print(f"\n[{i}/{len(messages)}] Sending...")
        send_telegram_message(message)
    
    print("\n" + "=" * 50)
    print("✅ Done!")
    print("=" * 50)


if __name__ == '__main__':
    main()
