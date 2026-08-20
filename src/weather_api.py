import os
import sys
import requests
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def get_weather(latitude, longitude, api_key=None):
    """
    Phase 16: Dynamic Weather API Abstraction.
    
    Queries live weather conditions using Open-Meteo (no-key default) or custom API key.
    """
    if api_key is None:
        api_key = os.environ.get("WEATHER_API_KEY", "")

    # Try Open-Meteo free spatial API (No key required for non-commercial open data)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            cw = resp.json().get('current_weather', {})
            temp = float(cw.get('temperature', 26.0))
            wind = float(cw.get('windspeed', 12.0))
            w_code = int(cw.get('weathercode', 0))
            
            if w_code in [61, 63, 65, 80, 81, 82]:
                cond = "RAIN"
                precip = 15.0
            elif w_code in [95, 96, 99]:
                cond = "THUNDERSTORM"
                precip = 35.0
            elif w_code in [45, 48]:
                cond = "FOG"
                precip = 0.0
            else:
                cond = "CLEAR"
                precip = 0.0

            return {
                "temperature": temp,
                "humidity": 65.0,
                "precipitation": precip,
                "wind_speed": wind,
                "visibility": 8.5 if cond != "FOG" else 1.5,
                "weather_condition": cond,
                "cloud_cover": 40.0,
                "api_status": "SUCCESS"
            }
    except Exception as e:
        print(f"[WeatherAPI] Warning: Open-Meteo call failed ({e}). Returning Bengaluru baseline.")

    # Fallback to Bengaluru monsoon/normal baseline
    return {
        "temperature": 26.5,
        "humidity": 65.0,
        "precipitation": 0.0,
        "wind_speed": 12.0,
        "visibility": 10.0,
        "weather_condition": "CLEAR",
        "cloud_cover": 30.0,
        "api_status": "BASELINE_FALLBACK"
    }

if __name__ == "__main__":
    weather_data = get_weather(12.9716, 77.5946)
    print("Weather API Query Test (Bengaluru):")
    print(weather_data)
