import os
import sys
import json
import urllib.request
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.neighbors import BallTree

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ensure_directories, OSM_DATA_DIR
from src.traffic_api import get_traffic
from src.weather_api import get_weather
from src.model_explainability import explain_road_risk

EARTH_RADIUS_KM = 6371.0088
MASTER_ROADS_CACHE = None
BALLTREE_CACHE = None
GEOCODE_CACHE = {}

def _load_master_roads():
    global MASTER_ROADS_CACHE, BALLTREE_CACHE
    if MASTER_ROADS_CACHE is None:
        csv_path = OSM_DATA_DIR / "road_master_features.csv"
        if not csv_path.exists():
            csv_path = OSM_DATA_DIR / "bengaluru_roads_with_accident_risk.csv"
        df = pd.read_csv(csv_path, low_memory=False)
        MASTER_ROADS_CACHE = df
        
        coords_rad = np.radians(df[['Road_Latitude', 'Road_Longitude']].values)
        BALLTREE_CACHE = BallTree(coords_rad, metric='haversine')
    return MASTER_ROADS_CACHE, BALLTREE_CACHE

def reverse_geocode(latitude, longitude):
    """
    Query OpenStreetMap Nominatim for exact real-world street and area name.
    """
    key = (round(latitude, 4), round(longitude, 4))
    if key in GEOCODE_CACHE:
        return GEOCODE_CACHE[key]
    
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}&zoom=18"
        req = urllib.request.Request(url, headers={'User-Agent': 'BengaluruRoadSafetyAI/2.0'})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            addr = data.get('address', {})
            
            road = addr.get('road') or addr.get('pedestrian') or addr.get('highway') or addr.get('suburb') or addr.get('neighbourhood')
            suburb = addr.get('suburb') or addr.get('neighbourhood') or addr.get('residential') or addr.get('city_district')
            city = addr.get('city') or addr.get('town') or 'Bengaluru'
            
            parts = [p for p in [road, suburb, city] if p]
            if parts:
                formatted = ", ".join(parts)
                GEOCODE_CACHE[key] = formatted
                return formatted
    except Exception:
        pass
    
    return None

def predict_road_risk(latitude, longitude, travel_speed_kmh=50.0):
    """
    Comprehensive real-world road safety & condition evaluation system.
    """
    ensure_directories()
    df_roads, tree = _load_master_roads()

    # 1. Match nearest mapped road segment
    point_rad = np.radians([[latitude, longitude]])
    dist_rad, idx = tree.query(point_rad, k=1)
    dist_km = float(dist_rad[0][0] * EARTH_RADIUS_KM)
    matched_row = df_roads.iloc[idx[0][0]].to_dict()

    # 2. Real-world Address Geocoding
    real_address = reverse_geocode(latitude, longitude)
    raw_road_name = str(matched_row.get('name', '')).strip()
    if raw_road_name in ['nan', '', 'None']:
        highway_type = str(matched_row.get('highway', 'road')).replace('_', ' ').title()
        raw_road_name = f"{highway_type} Road"
    
    if real_address:
        location_display = real_address
    else:
        location_display = f"{raw_road_name}, Bengaluru"

    # 3. Live Environmental & Traffic Data
    traffic = get_traffic(latitude, longitude)
    weather = get_weather(latitude, longitude)

    # 4. Feature Extraction & Scoring
    complexity = float(matched_row.get('road_complexity', 15.0))
    acc_avail = int(matched_row.get('Accident_Data_Available', 0))
    hist_risk = float(matched_row.get('Historical_Area_Accident_Risk', 0.0)) if acc_avail == 1 else 0.0
    damage_score = float(matched_row.get('road_damage_score', 25.0))
    design_speed = float(matched_row.get('maxspeed_kmh', 40.0))

    # Calculate Safety Risk Index (0 to 100)
    norm_hist = np.clip(hist_risk / 1500.0 * 30.0, 0, 30) if acc_avail == 1 else 10.0
    norm_comp = np.clip(complexity / 100.0 * 20.0, 0, 20)
    norm_dmg = np.clip(damage_score / 100.0 * 25.0, 0, 25)
    norm_cong = np.clip(traffic['congestion_level'] * 15.0, 0, 15)
    norm_speed = np.clip((travel_speed_kmh / design_speed) * 10.0, 0, 10)

    total_risk = round(norm_hist + norm_comp + norm_dmg + norm_cong + norm_speed, 1)
    final_risk = float(np.clip(total_risk, 0.0, 100.0))

    # Risk Levels & Actionable Driver Advice
    if final_risk >= 81.0:
        level = "SEVERE HAZARD"
        rec = "High accident area with severe road surface defects. Reduce speed immediately."
    elif final_risk >= 61.0:
        level = "HIGH RISK"
        rec = "Exercise caution. Moderate congestion, surface wear, or complex intersections detected."
    elif final_risk >= 31.0:
        level = "MODERATE RISK"
        rec = "Normal driving caution advised. Stay attentive to road conditions."
    else:
        level = "LOW RISK"
        rec = "Optimal driving conditions with good road surface and smooth traffic flow."

    # Road Surface Condition Descriptor
    if damage_score >= 60.0:
        surface_desc = "Severe Potholes & Cracks"
    elif damage_score >= 35.0:
        surface_desc = "Moderate Surface Wear & Bumps"
    else:
        surface_desc = "Smooth & Well-Maintained"

    # Illumination & Night Lighting Assessment
    lit_val = str(matched_row.get('lit', 'yes')).lower()
    if lit_val == 'yes':
        illumination_desc = "Good Night Lighting"
    else:
        illumination_desc = "Unlit / Poor Night Illumination"

    # Driving Safety Explanations
    matched_row['travel_speed_kmh'] = travel_speed_kmh
    matched_row['congestion_level'] = traffic['congestion_level']
    explanations = explain_road_risk(matched_row)

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "address": location_display,
            "road_type": str(matched_row.get('highway', 'Primary Road')).replace('_', ' ').title(),
            "distance_meters": max(5, int(dist_km * 1000))
        },
        "assessment": {
            "risk_score": final_risk,
            "risk_level": level,
            "travel_speed_kmh": travel_speed_kmh,
            "recommended_safe_speed": int(design_speed),
            "recommendation": rec
        },
        "road_condition": {
            "surface_status": surface_desc,
            "surface_damage_level": round(damage_score, 1),
            "junction_complexity": "High" if complexity > 25 else "Moderate" if complexity > 10 else "Standard",
            "traffic_flow": traffic['traffic_condition'],
            "illumination": illumination_desc,
            "weather": f"{weather['weather_condition']} ({weather['temperature']}°C)"
        },
        "safety_hazards": explanations['contributing_factors']
    }

if __name__ == "__main__":
    res = predict_road_risk(13.1007, 77.5963, travel_speed_kmh=70.0)
    print(json.dumps(res, indent=2))

