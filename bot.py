#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Iran Mountain Weather Bot - Compact Format
ربات پیش‌بینی آب و هوای قله‌های پرتردد ایران
"""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

# ============================================
# Configuration
# ============================================

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')
OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'

WEATHER_CODES = {
    0: '☀️ صاف', 1: '🌤️ صاف', 2: '⛅ نیمه‌ابری', 3: '☁️ ابری',
    45: '🌫️ مه', 48: '🌫️ مه',
    51: '🌦️ نم‌نم', 53: '🌦️ نم‌نم', 55: '🌦️ نم‌نم شدید',
    56: '🌧️ نم‌نم یخی', 57: '🌧️ نم‌نم یخی',
    61: '🌧️ باران خفیف', 63: '🌧️ باران', 65: '🌧️ باران شدید',
    66: '🌧️ باران یخی', 67: '🌧️ باران یخی',
    71: '❄️ برف خفیف', 73: '❄️ برف', 75: '❄️ برف شدید', 77: '❄️ برف',
    80: '🌧️ رگبار', 81: '🌧️ رگبار', 82: '🌧️ رگبار شدید',
    85: '🌨️ رگبار برف', 86: '🌨️ رگبار برف',
    95: '⛈️ طوفان', 96: '⛈️ طوفان', 99: '⛈️ طوفان شدید',
}

PERSIAN_DAYS = {
    0: 'دوشنبه', 1: 'سه‌شنبه', 2: 'چهارشنبه',
    3: 'پنجشنبه', 4: 'جمعه', 5: 'شنبه', 6: 'یکشنبه'
}

PERSIAN_MONTHS = [
    '', 'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
]


def load_mountains():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, 'mountains.json'), 'r', encoding='utf-8') as f:
        return json.load(f)['mountains']


def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + \
           ((gy2 + 399) // 400) + gd + g_d_m[gm - 1]
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def get_jalali_str(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    jy, jm, jd = gregorian_to_jalali(d.year, d.month, d.day)
    return f"{jd} {PERSIAN_MONTHS[jm]}"


def get_day_name(date_str):
    return PERSIAN_DAYS[datetime.strptime(date_str, '%Y-%m-%d').weekday()]


def get_weather_forecast(mountain, forecast_days=3):
    params = {
        'latitude': mountain['latitude'],
        'longitude': mountain['longitude'],
        'elevation': mountain['elevation'],
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,wind_speed_10m_max,wind_gusts_10m_max,weathercode',
        'timezone': 'Asia/Tehran',
        'forecast_days': forecast_days
    }
    try:
        req = urllib.request.Request(f"{OPEN_METEO_URL}?{urllib.parse.urlencode(params)}")
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {mountain['name']}: {e}")
        return None


def build_day_line(mountain, daily, day_index):
    """Build compact one-line for a mountain"""
    wc = daily['weathercode'][day_index]
    weather = WEATHER_CODES.get(wc, f'کد {wc}')
    tmin = daily['temperature_2m_min'][day_index]
    tmax = daily['temperature_2m_max'][day_index]
    wind = daily['wind_speed_10m_max'][day_index]
    precip = daily['precipitation_sum'][day_index]
    snow = daily['snowfall_sum'][day_index]

    extra = ''
    if precip > 0:
        extra += f' | 🌧{precip}mm'
    if snow > 0:
        extra += f' | ❄️{snow}cm'

    return f"⛰️ {mountain['name']} ({mountain['elevation']:,}م)\n{weather} | 🌡{tmin}°-{tmax}° | 💨{wind}km/h{extra}"


def build_messages(all_data):
    """Build 2 compact messages (day1 + day2)"""
    if not all_data or len(all_data[0][1]['daily']['time']) < 2:
        return []

    date1 = all_data[0][1]['daily']['time'][0]
    date2 = all_data[0][1]['daily']['time'][1]

    header1 = f"🏔 پیش‌بینی {get_day_name(date1)} {get_jalali_str(date1)}\n{'━' * 20}"
    header2 = f"🏔 پیش‌بینی {get_day_name(date2)} {get_jalali_str(date2)}\n{'━' * 20}"

    lines1 = [header1]
    lines2 = [header2]

    for mountain, weather in all_data:
        if weather and 'daily' in weather:
            lines1.append(build_day_line(mountain, weather['daily'], 0))
            lines2.append(build_day_line(mountain, weather['daily'], 1))

    msg1 = '\n\n'.join(lines1)
    msg2 = '\n\n'.join(lines2)

    return [msg1, msg2]


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("No Telegram credentials set")
        print(text)
        print("---")
        return False
    try:
        data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': text}).encode('utf-8')
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get('ok'):
                print(f"✅ Sent")
                return True
            else:
                print(f"❌ {result.get('description')}")
                return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("=" * 50)
    print("🏔️ Iran Mountain Weather Bot")
    print("=" * 50)

    mountains = load_mountains()
    print(f"📋 {len(mountains)} mountains loaded")

    all_data = []
    for i, m in enumerate(mountains, 1):
        print(f"[{i}/{len(mountains)}] {m['name']}...", end=' ')
        weather = get_weather_forecast(m)
        if weather:
            all_data.append((m, weather))
            print("✅")
        else:
            print("❌")

    messages = build_messages(all_data)
    print(f"\n📤 Sending {len(messages)} messages...")

    for i, msg in enumerate(messages, 1):
        print(f"\nMessage {i}/{len(messages)}:")
        print(msg)
        send_telegram(msg)

    print("\n" + "=" * 50)
    print("✅ Done!")


if __name__ == '__main__':
    main()
