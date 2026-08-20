import os
import sys
import json
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

def predict_road_risk(latitude, longitude, travel_speed_kmh=50.0):
    """
    Phase 21: End-to-End Location Query System for Bengaluru Road Segment Safety Assessment.
    """
    ensure_directories()
    df_roads, tree = _load_master_roads()

    # 1. Match nearest OSM road segment
    point_rad = np.radians([[latitude, longitude]])
    dist_rad, idx = tree.query(point_rad, k=1)
    dist_km = float(dist_rad[0][0] * EARTH_RADIUS_KM)
    matched_row = df_roads.iloc[idx[0][0]].to_dict()

    # 2. Query Live APIs
    traffic = get_traffic(latitude, longitude)
    weather = get_weather(latitude, longitude)

    # 3. Extract Features
    road_id = matched_row.get('road_id', 'BLR_OSM_UNKNOWN')
    road_name = str(matched_row.get('name', 'Unnamed Bengaluru Road'))
    if road_name == 'nan':
        road_name = f"OSM Segment ({matched_row.get('highway', 'road')})"

    complexity = float(matched_row.get('road_complexity', 15.0))
    acc_avail = int(matched_row.get('Accident_Data_Available', 0))
    hist_risk = float(matched_row.get('Historical_Area_Accident_Risk', 0.0)) if acc_avail == 1 else 0.0
    damage_score = float(matched_row.get('road_damage_score', 0.0))

    # 4. Calculate Combined Risk Score (0 - 100)
    norm_hist = np.clip(hist_risk / 1500.0 * 30.0, 0, 30) if acc_avail == 1 else 10.0
    norm_comp = np.clip(complexity / 100.0 * 20.0, 0, 20)
    norm_dmg = np.clip(damage_score / 100.0 * 25.0, 0, 25)
    norm_cong = np.clip(traffic['congestion_level'] * 15.0, 0, 15)
    norm_speed = np.clip((travel_speed_kmh / float(matched_row.get('maxspeed_kmh', 40.0))) * 10.0, 0, 10)

    total_risk = round(norm_hist + norm_comp + norm_dmg + norm_cong + norm_speed, 2)
    final_risk = float(np.clip(total_risk, 0.0, 100.0))

    if final_risk >= 81.0:
        level = "VERY HIGH"
        rec = "Reduce travel speed immediately. High accident area with road hazards."
    elif final_risk >= 61.0:
        level = "HIGH"
        rec = "Exercise extra caution. Moderate to high congestion and damage detected."
    elif final_risk >= 31.0:
        level = "MODERATE"
        rec = "Standard driving caution advised."
    else:
        level = "LOW"
        rec = "Optimal driving conditions."

    # 5. Explanations
    matched_row['travel_speed_kmh'] = travel_speed_kmh
    matched_row['congestion_level'] = traffic['congestion_level']
    explanations = explain_road_risk(matched_row)

    return {
        "location": {
            "query_latitude": latitude,
            "query_longitude": longitude,
            "nearest_road_id": road_id,
            "nearest_road_name": road_name,
            "distance_to_segment_km": round(dist_km, 3)
        },
        "assessment": {
            "risk_score": final_risk,
            "risk_level": level,
            "travel_speed_kmh": travel_speed_kmh,
            "recommendation": rec
        },
        "contributing_factors": explanations['contributing_factors'],
        "feature_breakdown": {
            "historical_accident_area_risk": "Available" if acc_avail == 1 else "Unknown",
            "historical_accidents_count": int(hist_risk) if acc_avail == 1 else None,
            "road_complexity_score": complexity,
            "road_damage_score": damage_score,
            "traffic_condition": traffic['traffic_condition'],
            "congestion_level": traffic['congestion_level'],
            "weather_condition": weather['weather_condition'],
            "temperature_celsius": weather['temperature']
        }
    }

if __name__ == "__main__":
    # Test location query for Yelahanka, Bengaluru (13.1007, 77.5963)
    res = predict_road_risk(13.1007, 77.5963, travel_speed_kmh=70.0)
    print("Location Risk Assessment Test:")
    print(json.dumps(res, indent=2))
