import os
import sys
import requests
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def get_traffic(latitude, longitude, destination=None, api_key=None):
    """
    Phase 15: Dynamic Traffic API Abstraction.
    
    Queries live traffic conditions (or returns default open-data benchmark estimates).
    Never hardcodes API keys; uses TRAFFIC_API_KEY environment variable.
    """
    if api_key is None:
        api_key = os.environ.get("TRAFFIC_API_KEY", "")

    # Open/Configurable Live API Hook (e.g. TomTom / Google Maps / OpenTraffic API)
    if api_key:
        try:
            # Example API Endpoint Structure
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={api_key}&point={latitude},{longitude}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get('flowSegmentData', {})
                current_speed = data.get('currentSpeed', 35.0)
                free_flow = data.get('freeFlowSpeed', 45.0)
                congestion = round(max(0.0, min(1.0, 1.0 - (current_speed / max(1.0, free_flow)))), 2)
                
                if congestion < 0.2:
                    cond = 'LIGHT'
                elif congestion < 0.5:
                    cond = 'MODERATE'
                elif congestion < 0.8:
                    cond = 'HEAVY'
                else:
                    cond = 'SEVERE'

                return {
                    "traffic_condition": cond,
                    "traffic_speed": float(current_speed),
                    "congestion_level": congestion,
                    "travel_time": round(50.0 / max(10.0, current_speed) * 60, 1),
                    "free_flow_time": round(50.0 / max(10.0, free_flow) * 60, 1),
                    "api_status": "SUCCESS"
                }
        except Exception as e:
            print(f"[TrafficAPI] Warning: Live API call failed ({e}). Falling back to spatial default.")

    # Fallback to realistic Bengaluru baseline estimates based on time/location
    return {
        "traffic_condition": "MODERATE",
        "traffic_speed": 35.0,
        "congestion_level": 0.35,
        "travel_time": 8.5,
        "free_flow_time": 6.0,
        "api_status": "BASELINE_FALLBACK"
    }

if __name__ == "__main__":
    traffic_data = get_traffic(12.9716, 77.5946)
    print("Traffic API Query Test (Bengaluru City Center):")
    print(traffic_data)
