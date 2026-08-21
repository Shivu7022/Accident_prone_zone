import os
import sys
import json
import pandas as pd
from pathlib import Path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# Ensure root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import ACCIDENT_DATA_DIR, OSM_DATA_DIR
from src.inference import predict_road_risk
from src.traffic_api import get_traffic
from src.weather_api import get_weather
from src.road_damage import calculate_road_damage_score

@api_view(['GET'])
def health_check(request):
    """
    Health check endpoint returning service status.
    """
    return Response({
        "status": "healthy",
        "service": "Bengaluru Road Safety Risk Django API",
        "framework": "Django REST Framework",
        "version": "1.0.0"
    })

@api_view(['POST'])
def predict_risk_endpoint(request):
    """
    Predict road safety risk score for given coordinates and travel speed.
    """
    data = request.data or {}
    try:
        latitude = float(data.get('latitude', 12.9716))
        longitude = float(data.get('longitude', 77.5946))
        travel_speed_kmh = float(data.get('travel_speed_kmh', 50.0))
        
        result = predict_road_risk(latitude, longitude, travel_speed_kmh)
        return Response(result)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_accident_hotspots(request):
    """
    Return list of accident hotspots in Bengaluru.
    """
    csv_path = ACCIDENT_DATA_DIR / "accident_hotspots.csv"
    if not csv_path.exists():
        # Fallback default hotspots if CSV doesn't exist
        default_hotspots = [
            {"Station": "Yelahanka", "Latitude": 13.1007, "Longitude": 77.5963, "Total_Accidents": 1530, "Risk_Level": "VERY HIGH"},
            {"Station": "K R Puram", "Latitude": 13.0075, "Longitude": 77.6959, "Total_Accidents": 1500, "Risk_Level": "VERY HIGH"},
            {"Station": "Kamakshipalya", "Latitude": 12.9806, "Longitude": 77.5255, "Total_Accidents": 1329, "Risk_Level": "HIGH"},
            {"Station": "Peenya", "Latitude": 13.0329, "Longitude": 77.5273, "Total_Accidents": 1201, "Risk_Level": "HIGH"},
            {"Station": "Whitefield", "Latitude": 12.9698, "Longitude": 77.7499, "Total_Accidents": 980, "Risk_Level": "MEDIUM"},
        ]
        return Response(default_hotspots)
    
    try:
        df = pd.read_csv(csv_path)
        return Response(df.to_dict(orient="records"))
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_road_info(request, road_id):
    """
    Return road feature dataset row for specific road_id.
    """
    csv_path = OSM_DATA_DIR / "road_master_features.csv"
    if not csv_path.exists():
        return Response({"error": "Master road feature dataset not found."}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        df = pd.read_csv(csv_path, low_memory=False)
        matched = df[df['road_id'] == road_id]
        if matched.empty:
            return Response({"error": f"Road segment '{road_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(matched.iloc[0].to_dict())
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def calculate_damage_endpoint(request):
    """
    Calculate road damage score from YOLO bounding box detections.
    """
    detections = request.data.get('detections', [])
    res = calculate_road_damage_score(detections)
    return Response(res)

@api_view(['GET'])
def get_traffic_endpoint(request):
    """
    Get live/simulated traffic data for lat/lon.
    """
    lat = float(request.GET.get('lat', 12.9716))
    lon = float(request.GET.get('lon', 77.5946))
    return Response(get_traffic(lat, lon))

@api_view(['GET'])
def get_weather_endpoint(request):
    """
    Get live/simulated weather data for lat/lon.
    """
    lat = float(request.GET.get('lat', 12.9716))
    lon = float(request.GET.get('lon', 77.5946))
    return Response(get_weather(lat, lon))

@api_view(['GET'])
def search_location(request):
    """
    Geocode search query to latitude and longitude using Nominatim.
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return Response([])

    import urllib.request
    import urllib.parse
    
    # Append Bengaluru context if not explicitly contained
    search_q = query if 'bengaluru' in query.lower() or 'bangalore' in query.lower() else f"{query}, Bengaluru"
    url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(search_q)}&limit=5"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'BengaluruRoadSafetyAI/2.0'})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            results = json.loads(resp.read().decode('utf-8'))
            formatted = [
                {
                    "display_name": item.get('display_name'),
                    "lat": float(item.get('lat')),
                    "lon": float(item.get('lon'))
                }
                for item in results
            ]
            return Response(formatted)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def reverse_geocode_endpoint(request):
    """
    Reverse geocode latitude and longitude to real-world address.
    """
    try:
        lat = float(request.GET.get('lat', 12.9716))
        lon = float(request.GET.get('lon', 77.5946))
        from src.inference import reverse_geocode
        address = reverse_geocode(lat, lon)
        return Response({"address": address or f"{lat:.4f}°N, {lon:.4f}°E"})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

