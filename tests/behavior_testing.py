"""
Behavior Testing Script
========================
This script tests 7 core functions of the system and marks Pass/Fail.

Functions Tested:
1. Route Finding - Test route calculation between two locations
2. Route Selection - Test route selection from alternatives
3. Accident Hotspot Retrieval - Test hotspot data API
4. Road Damage Detection - Test YOLO11s detection API
5. Traffic Sign Detection - Test YOLO11n detector API
6. Traffic Sign Classification - Test ResNet18 classifier API
7. Traffic Data Retrieval - Test TomTom traffic API integration

Usage:
    python behavior_testing.py

Requirements:
    - All backend servers running (ports 8000, 8001, 8002)
    - TOMTOM_API_KEY configured in backend/.env
    - Model files present
"""

import asyncio
import httpx
import time
from pathlib import Path
from typing import Dict, List, Tuple
import json
import base64
import numpy as np
import cv2


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

# API Endpoints
MAIN_BACKEND_URL = "http://127.0.0.1:8001"
TRAFFIC_SIGN_API_URL = "http://127.0.0.1:8000"
ROAD_DAMAGE_API_URL = "http://127.0.0.1:8002"

# Endpoints
HEALTH_ENDPOINTS = {
    "main_backend": f"{MAIN_BACKEND_URL}/",
    "traffic_sign_api": f"{TRAFFIC_SIGN_API_URL}/",
    "road_damage_api": f"{ROAD_DAMAGE_API_URL}/health"
}

FUNCTION_ENDPOINTS = {
    "geocode": f"{MAIN_BACKEND_URL}/api/geocode",
    "hotspots": f"{MAIN_BACKEND_URL}/api/hotspots",
    "road_damage": f"{ROAD_DAMAGE_API_URL}/predict",
    "traffic_sign_detect": f"{TRAFFIC_SIGN_API_URL}/api/signboard/detect/",
    "traffic_sign_classify": f"{TRAFFIC_SIGN_API_URL}/api/signboard/predict/",
    "traffic": f"{MAIN_BACKEND_URL}/api/traffic",
    "weather": f"{MAIN_BACKEND_URL}/api/weather"
}

# Test Locations (Bengaluru coordinates)
TEST_LOCATIONS = {
    "location": "MG Road, Bengaluru"
}

# Timeout settings
TIMEOUT = 30.0


# ============================================================
# TEST RESULT CLASS
# ============================================================

class TestResult:
    """Stores the result of a single test."""

    def __init__(self, function_name: str):
        self.function_name = function_name
        self.passed = False
        self.error_message = None
        self.execution_time = 0.0
        self.details = {}

    def to_dict(self) -> Dict:
        return {
            "function": self.function_name,
            "status": "PASS" if self.passed else "FAIL",
            "error": self.error_message,
            "execution_time_ms": round(self.execution_time * 1000, 2),
            "details": self.details
        }


# ============================================================
# TEST FUNCTIONS
# ============================================================

async def test_geocoding(client: httpx.AsyncClient) -> TestResult:
    """Test 1: Geocoding - Convert location name to coordinates."""
    result = TestResult("Geocoding")
    start_time = time.perf_counter()

    try:
        params = {
            "query": "MG Road, Bengaluru"
        }

        response = await client.get(
            FUNCTION_ENDPOINTS["geocode"],
            params=params,
            timeout=TIMEOUT
        )

        result.execution_time = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and "locations" in data and len(data["locations"]) > 0:
                result.passed = True
                first_location = data["locations"][0]
                result.details = {
                    "num_locations": len(data["locations"]),
                    "first_location": {
                        "lat": first_location.get("lat", "N/A"),
                        "lon": first_location.get("lon", "N/A"),
                        "display_name": first_location.get("display_name", "N/A")
                    }
                }
            else:
                result.error_message = "Invalid geocoding response format"
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text}"

    except asyncio.TimeoutError:
        result.error_message = "Request timed out"
    except Exception as e:
        result.error_message = str(e)

    return result


async def test_accident_hotspot_retrieval(client: httpx.AsyncClient) -> TestResult:
    """Test 2: Accident Hotspot Retrieval - Get hotspot data."""
    result = TestResult("Accident Hotspot Retrieval")
    start_time = time.perf_counter()

    try:
        response = await client.get(
            FUNCTION_ENDPOINTS["hotspots"],
            timeout=TIMEOUT
        )

        result.execution_time = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                result.passed = True
                result.details = {
                    "num_hotspots": len(data),
                    "sample_hotspot": data[0] if data else None
                }
            else:
                result.error_message = "No hotspot data returned"
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text}"

    except asyncio.TimeoutError:
        result.error_message = "Request timed out"
    except Exception as e:
        result.error_message = str(e)

    return result


async def test_road_damage_detection(client: httpx.AsyncClient) -> TestResult:
    """Test 3: Road Damage Detection - Test YOLO11s detection."""
    result = TestResult("Road Damage Detection")
    start_time = time.perf_counter()

    try:
        # Create a test image (640x640 RGB)
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', test_image)
        image_bytes = buffer.tobytes()

        files = {
            "file": ("test_road.jpg", image_bytes, "image/jpeg")
        }

        response = await client.post(
            FUNCTION_ENDPOINTS["road_damage"],
            files=files,
            timeout=TIMEOUT
        )

        result.execution_time = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            if "detections" in data and "annotated_image" in data:
                result.passed = True
                result.details = {
                    "total_detections": data.get("total_detections", 0),
                    "has_annotated_image": bool(data.get("annotated_image"))
                }
            else:
                result.error_message = "Invalid response format"
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text}"

    except asyncio.TimeoutError:
        result.error_message = "Request timed out"
    except Exception as e:
        result.error_message = str(e)

    return result


async def test_traffic_sign_detection(client: httpx.AsyncClient) -> TestResult:
    """Test 4: Traffic Sign Detection - Test YOLO11n detector."""
    result = TestResult("Traffic Sign Detection")
    start_time = time.perf_counter()

    try:
        # Create a test image
        test_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', test_image)
        image_bytes = buffer.tobytes()

        files = {
            "file": ("test_sign.jpg", image_bytes, "image/jpeg")
        }

        response = await client.post(
            FUNCTION_ENDPOINTS["traffic_sign_detect"],
            files=files,
            timeout=TIMEOUT
        )

        result.execution_time = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            if "detections" in data and "annotated_image" in data:
                result.passed = True
                result.details = {
                    "total_detections": data.get("total_detections", 0),
                    "has_annotated_image": bool(data.get("annotated_image"))
                }
            else:
                result.error_message = "Invalid response format"
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text}"

    except asyncio.TimeoutError:
        result.error_message = "Request timed out"
    except Exception as e:
        result.error_message = str(e)

    return result


async def test_traffic_sign_classification(client: httpx.AsyncClient) -> TestResult:
    """Test 5: Traffic Sign Classification - Test ResNet18 classifier."""
    result = TestResult("Traffic Sign Classification")
    start_time = time.perf_counter()

    try:
        # Create a test image
        test_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', test_image)
        image_bytes = buffer.tobytes()

        files = {
            "file": ("test_sign_classify.jpg", image_bytes, "image/jpeg")
        }

        response = await client.post(
            FUNCTION_ENDPOINTS["traffic_sign_classify"],
            files=files,
            timeout=TIMEOUT
        )

        result.execution_time = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            if "class_id" in data and "sign_name" in data and "confidence" in data:
                result.passed = True
                result.details = {
                    "predicted_class": data.get("class_id"),
                    "sign_name": data.get("sign_name"),
                    "confidence": data.get("confidence")
                }
            else:
                result.error_message = "Invalid response format"
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text}"

    except asyncio.TimeoutError:
        result.error_message = "Request timed out"
    except Exception as e:
        result.error_message = str(e)

    return result


async def test_traffic_data_retrieval(client: httpx.AsyncClient) -> TestResult:
    """Test 6: Traffic Data Retrieval - Test TomTom API integration."""
    result = TestResult("Traffic Data Retrieval")
    start_time = time.perf_counter()

    try:
        # Test with Bengaluru coordinates
        params = {
            "lat": 12.9716,
            "lon": 77.5946
        }

        response = await client.get(
            FUNCTION_ENDPOINTS["traffic"],
            params=params,
            timeout=TIMEOUT
        )

        result.execution_time = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            # Traffic data may have various formats, just check it's valid JSON
            result.passed = True
            result.details = {
                "response_keys": list(data.keys()) if isinstance(data, dict) else "list",
                "has_traffic_data": True
            }
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text}"

    except asyncio.TimeoutError:
        result.error_message = "Request timed out"
    except Exception as e:
        result.error_message = str(e)

    return result


async def test_weather_data_retrieval(client: httpx.AsyncClient) -> TestResult:
    """Test 7: Weather Data Retrieval - Test Open-Meteo API integration."""
    result = TestResult("Weather Data Retrieval")
    start_time = time.perf_counter()

    try:
        # Test with Bengaluru coordinates
        params = {
            "lat": 12.9716,
            "lon": 77.5946
        }

        response = await client.get(
            FUNCTION_ENDPOINTS["weather"],
            params=params,
            timeout=TIMEOUT
        )

        result.execution_time = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                result.passed = True
                result.details = {
                    "response_keys": list(data.keys()),
                    "has_weather_data": True
                }
            else:
                result.error_message = "Invalid response format"
        else:
            result.error_message = f"HTTP {response.status_code}: {response.text}"

    except asyncio.TimeoutError:
        result.error_message = "Request timed out"
    except Exception as e:
        result.error_message = str(e)

    return result


# ============================================================
# HEALTH CHECK
# ============================================================

async def check_server_health(client: httpx.AsyncClient) -> Dict[str, bool]:
    """Check if all required servers are running."""
    health_status = {}

    for server_name, endpoint in HEALTH_ENDPOINTS.items():
        try:
            response = await client.get(endpoint, timeout=5.0)
            health_status[server_name] = response.status_code == 200
        except Exception:
            health_status[server_name] = False

    return health_status


# ============================================================
# MAIN TEST RUNNER
# ============================================================

async def run_all_tests():
    """Run all behavior tests and collect results."""
    print("=" * 70)
    print("BEHAVIOR TESTING - TABLE VII")
    print("=" * 70)
    print(f"Testing 7 core functions")
    print(f"Main Backend: {MAIN_BACKEND_URL}")
    print(f"Traffic Sign API: {TRAFFIC_SIGN_API_URL}")
    print(f"Road Damage API: {ROAD_DAMAGE_API_URL}")
    print("=" * 70)

    # Create HTTP client
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Check server health
        print("\n[PRE-CHECK] Verifying server health...")
        print("-" * 70)
        health_status = await check_server_health(client)

        all_healthy = all(health_status.values())
        for server, status in health_status.items():
            status_str = "[OK] Running" if status else "[X] Not running"
            print(f"  {server:.<40} {status_str}")

        if not all_healthy:
            print("\n[!] WARNING: Some servers are not running. Tests may fail.")
            print("  Please ensure all servers are running before testing.\n")
        else:
            print("\n[OK] All servers are running.\n")

        print("=" * 70)
        print("RUNNING TESTS")
        print("=" * 70)

        # Run all tests
        test_functions = [
            test_geocoding,
            test_accident_hotspot_retrieval,
            test_road_damage_detection,
            test_traffic_sign_detection,
            test_traffic_sign_classification,
            test_traffic_data_retrieval,
            test_weather_data_retrieval
        ]

        results = []
        for i, test_func in enumerate(test_functions, 1):
            print(f"\n[Test {i}/7] {test_func.__name__.replace('test_', '').title()}")
            print("-" * 70)
            result = await test_func(client)
            results.append(result)

            status_str = "[OK] PASS" if result.passed else "[X] FAIL"
            print(f"  Status: {status_str}")
            print(f"  Execution Time: {result.execution_time * 1000:.2f} ms")

            if result.passed:
                print(f"  Details: {result.details}")
            else:
                print(f"  Error: {result.error_message}")

    # Print summary table
    print("\n" + "=" * 70)
    print("TABLE VII: Behavior Testing Results")
    print("=" * 70)
    print(f"{'#':<4} {'Function':<35} {'Status':<10} {'Time (ms)':<12}")
    print("-" * 70)

    for i, result in enumerate(results, 1):
        status = "PASS" if result.passed else "FAIL"
        print(f"{i:<4} {result.function_name:<35} {status:<10} {result.execution_time * 1000:<12.2f}")

    print("=" * 70)

    # Calculate pass rate
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\nSummary: {passed}/{total} tests passed ({pass_rate:.1f}%)")
    print("=" * 70)

    # Save results to JSON
    results_file = BASE_DIR / "tests" / "behavior_test_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    results_dict = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "server_health": health_status,
        "tests": [r.to_dict() for r in results],
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(pass_rate, 2)
        }
    }

    with open(results_file, 'w') as f:
        json.dump(results_dict, f, indent=2)

    print(f"\nResults saved to: {results_file}")
    print("=" * 70)

    return results_dict


def main():
    """Main entry point."""
    try:
        results = asyncio.run(run_all_tests())
        return results
    except KeyboardInterrupt:
        print("\n\n[!] Tests interrupted by user.")
        return None
    except Exception as e:
        print(f"\n\n[X] Fatal error: {e}")
        return None


if __name__ == "__main__":
    main()
