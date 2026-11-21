import unittest
import math
import httpx
import sys
from pathlib import Path

# Add project roots to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

# Import navigation math helpers
from frontend_math import (
    calculate_distance,
    calculate_bearing,
    smooth_angle,
    snap_to_route,
)

BASE_URL = "http://127.0.0.1:8001"

class TestNavigationSystem(unittest.TestCase):

    def test_01_geocoding_api(self):
        """Test location search and geocoding API"""
        response = httpx.get(f"{BASE_URL}/api/geocode?query=Majestic,Bengaluru")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("locations", data)
        self.assertTrue(len(data["locations"]) > 0)
        first = data["locations"][0]
        self.assertIn("lat", first)
        self.assertIn("lon", first)

    def test_02_routing_api(self):
        """Test route generation API proxy"""
        start_lon, start_lat = 77.5946, 12.9716 # Bengaluru Center
        dest_lon, dest_lat = 77.5800, 13.0000  # Yeshwanthpur area
        url = f"{BASE_URL}/api/routes?start_lon={start_lon}&start_lat={start_lat}&dest_lon={dest_lon}&dest_lat={dest_lat}&alternatives=true"
        response = httpx.get(url, timeout=10.0)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("code"), "Ok")
        self.assertTrue(len(data.get("routes", [])) > 0)

    def test_03_traffic_api(self):
        """Test TomTom traffic flow endpoint"""
        response = httpx.get(f"{BASE_URL}/api/traffic?lat=12.9716&lon=77.5946")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("current_speed_kmh", data)

    def test_04_weather_api(self):
        """Test Open-Meteo weather endpoint"""
        response = httpx.get(f"{BASE_URL}/api/weather?lat=12.9716&lon=77.5946")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("temperature", data)
        self.assertIn("weather_condition", data)

    def test_05_accident_hotspots_api(self):
        """Test historical accident hotspots endpoint"""
        response = httpx.get(f"{BASE_URL}/api/hotspots")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertTrue(len(data) > 0)

    def test_06_ml_health_endpoints(self):
        """Test ML proxy health status endpoints"""
        damage_health = httpx.get(f"{BASE_URL}/api/roaddamage/health")
        self.assertEqual(damage_health.status_code, 200)
        sign_health = httpx.get(f"{BASE_URL}/api/signboard/health")
        self.assertEqual(sign_health.status_code, 200)

    def test_07_heading_wrap_around_math(self):
        """Test 0°/360° heading wrap-around calculation without full circle spin"""
        # Moving from 350° to 10° should rotate +20°, not -340°
        current = 350.0
        target = 10.0
        smoothed = smooth_angle(current, target, alpha=0.5)
        self.assertAlmostEqual(smoothed, 0.0, delta=1.0)

        # Moving from 10° to 350° should rotate -20°, not +340°
        current = 10.0
        target = 350.0
        smoothed = smooth_angle(current, target, alpha=0.5)
        self.assertAlmostEqual(smoothed, 0.0, delta=1.0)

    def test_08_route_snapping_and_off_route(self):
        """Test snap-to-route and off-route threshold detection"""
        route_geom = [
            (12.9716, 77.5946),
            (12.9750, 77.5946),
            (12.9800, 77.5946)
        ]
        # Point close to route (5 meters off)
        snapped = snap_to_route(12.9725, 77.59465, route_geom)
        self.assertFalse(snapped["is_off_route"])
        self.assertLess(snapped["distance"], 15.0)

        # Point far from route (150 meters off)
        far_point = snap_to_route(12.9725, 77.59650, route_geom)
        self.assertTrue(far_point["is_off_route"])

if __name__ == "__main__":
    unittest.main()
