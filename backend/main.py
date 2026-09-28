import asyncio
import math
import os
import re
import time
from pathlib import Path
import httpx
import pandas as pd
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
GEOCODE_CACHE = {}
GEOCODE_LOCK = asyncio.Lock()
GEOCODE_LAST_REQUEST = 0.0

TOMTOM_TRAFFIC_URL = (
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/"
    "absolute/10/json"
)

app = FastAPI(
    title="Bengaluru Accident Prone Zone Detection API",
    version="1.0.0",
)

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

HOTSPOT_FILE = DATA_DIR / "bengaluru_accident_risk_analysis.csv"
ZONE_FILE = DATA_DIR / "bengaluru_zone_accident_summary.csv"
YEARLY_FILE = DATA_DIR / "bengaluru_yearly_accident_summary.csv"

MAP_FILE = STATIC_DIR / "bengaluru_accident_hotspot_map.html"

# OSM Road Network Files
URBAN_ROADS_FILE = DATA_DIR / "bengaluru_urban_roads.csv"
RURAL_ROADS_FILE = DATA_DIR / "bengaluru_rural_roads.csv"

SIGNBOARD_API_URL = "http://127.0.0.1:8000/api/signboard/predict/"
SIGNBOARD_HEALTH_URL = "http://127.0.0.1:8000/"
SIGNBOARD_DETECT_URL = "http://127.0.0.1:8000/api/signboard/detect/"

ROAD_DAMAGE_API_URL = "http://127.0.0.1:8002/predict"
ROAD_DAMAGE_HEALTH_URL = "http://127.0.0.1:8002/health"


DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# --------------------------------------------------
# CLEAN NAN VALUES
# --------------------------------------------------

def clean_nan(data):

    if isinstance(data, dict):
        return {
            key: clean_nan(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [
            clean_nan(value)
            for value in data
        ]

    if data is None:
        return None

    if isinstance(data, float) and not math.isfinite(data):
        return None

    try:
        if pd.isna(data):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(data, "item"):
        try:
            return clean_nan(data.item())
        except (ValueError, TypeError):
            pass

    return data


# --------------------------------------------------
# READ CSV FILES
# --------------------------------------------------

def read_csv_data(file_path: Path):

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Data file not found: {file_path.name}",
        )

    try:
        df = pd.read_csv(file_path)

        df = df.astype(object)
        df = df.where(pd.notna(df), None)

        return clean_nan(
            df.to_dict(orient="records")
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading {file_path.name}: {str(error)}",
        )


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "Bengaluru Accident Prone Zone Detection API is running",
        "docs": "/docs",
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health_check():

    return {
        "status": "running",
        "hotspot_data_exists": HOTSPOT_FILE.exists(),
        "zone_data_exists": ZONE_FILE.exists(),
        "yearly_data_exists": YEARLY_FILE.exists(),
        "map_exists": MAP_FILE.exists(),
    }


# --------------------------------------------------
# ACCIDENT HOTSPOTS
# --------------------------------------------------

@app.get("/api/hotspots")
def get_hotspots():

    return read_csv_data(HOTSPOT_FILE)


@app.get("/api/geocode")
async def geocode_location(query: str):
    global GEOCODE_LAST_REQUEST

    normalized_query = query.strip()
    if not normalized_query or len(normalized_query) > 200:
        raise HTTPException(
            status_code=400,
            detail="Enter a location name up to 200 characters.",
        )

    cache_key = normalized_query.casefold()
    if cache_key in GEOCODE_CACHE:
        return {"locations": GEOCODE_CACHE[cache_key]}

    async with GEOCODE_LOCK:
        if cache_key in GEOCODE_CACHE:
            return {"locations": GEOCODE_CACHE[cache_key]}

        wait_seconds = 1 - (time.monotonic() - GEOCODE_LAST_REQUEST)
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        try:
            async with httpx.AsyncClient(
                timeout=20,
                headers={
                    "User-Agent": "RoadSafeNavigator/1.0 (location search)",
                },
            ) as client:
                response = await client.get(
                    NOMINATIM_URL,
                    params={
                        "q": normalized_query,
                        "format": "jsonv2",
                        "limit": 5,
                        "addressdetails": 1,
                    },
                )
                response.raise_for_status()
                results = response.json()
        except httpx.HTTPError as error:
            raise HTTPException(
                status_code=502,
                detail=f"Location search is unavailable: {error}",
            ) from error
        finally:
            GEOCODE_LAST_REQUEST = time.monotonic()

        locations = [
            {
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
                "display_name": item["display_name"],
                "type": item.get("type"),
            }
            for item in results
            if item.get("lat") and item.get("lon") and item.get("display_name")
        ]
        GEOCODE_CACHE[cache_key] = locations
        return {"locations": locations}


# --------------------------------------------------
# ZONE SUMMARY
# --------------------------------------------------

@app.get("/api/zones")
def get_zones():

    return read_csv_data(ZONE_FILE)


# --------------------------------------------------
# YEARLY ACCIDENT SUMMARY
# --------------------------------------------------

@app.get("/api/yearly")
def get_yearly_data():

    return read_csv_data(YEARLY_FILE)


# --------------------------------------------------
# MAP
# --------------------------------------------------

@app.get("/api/map")
def get_map():

    if not MAP_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="Accident hotspot map HTML file not found.",
        )

    return FileResponse(
        str(MAP_FILE),
        media_type="text/html",
    )


# --------------------------------------------------
# TRAFFIC SIGN HEALTH
# --------------------------------------------------

@app.get("/api/signboard/health")
async def signboard_health():

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.get(
                SIGNBOARD_HEALTH_URL
            )

        return {
            "status": (
                "connected"
                if response.is_success
                else "disconnected"
            ),
            "traffic_sign_api_status": response.status_code,
            "detector_loaded": response.json().get("detector_loaded", False),
            "detector_name": response.json().get("detector_name"),
        }

    except Exception as error:

        return {
            "status": "disconnected",
            "message": str(error),
        }


# --------------------------------------------------
# TRAFFIC SIGN PREDICTION
# --------------------------------------------------

@app.post("/api/signboard/predict")
async def predict_signboard(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if (
        not file.content_type
        or not file.content_type.startswith("image/")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image.",
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:

            response = await client.post(
                SIGNBOARD_API_URL,
                files={
                    "file": (
                        file.filename,
                        image_bytes,
                        file.content_type,
                    )
                },
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )

        return clean_nan(response.json())

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail=f"Traffic sign API error: {str(error)}",
        )


@app.post("/api/signboard/detect")
async def detect_signboard_regions(
    file: UploadFile = File(...)
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                SIGNBOARD_DETECT_URL,
                files={
                    "file": (
                        file.filename,
                        image_bytes,
                        file.content_type,
                    )
                },
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )

        return clean_nan(response.json())
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Traffic-sign detector error: {error}",
        ) from error


# --------------------------------------------------
# ROAD DAMAGE HEALTH
# --------------------------------------------------

@app.get("/api/roaddamage/health")
async def road_damage_health():

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.get(
                ROAD_DAMAGE_HEALTH_URL
            )

        return {
            "status": (
                "connected"
                if response.is_success
                else "disconnected"
            ),
            "road_damage_api_status": response.status_code,
        }

    except Exception as error:

        return {
            "status": "disconnected",
            "message": str(error),
        }


# --------------------------------------------------
# ROAD DAMAGE PREDICTION
# --------------------------------------------------

@app.post("/api/roaddamage/predict")
async def predict_road_damage(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected.",
        )

    if (
        not file.content_type
        or not file.content_type.startswith("image/")
    ):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid image.",
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:

            response = await client.post(
                ROAD_DAMAGE_API_URL,
                files={
                    "file": (
                        file.filename,
                        image_bytes,
                        file.content_type,
                    )
                },
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )

        return clean_nan(response.json())

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail=f"Road damage API error: {str(error)}",
        )


@app.get("/api/traffic")
async def get_traffic(lat: float = 12.9716, lon: float = 77.5946):
    if not TOMTOM_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="TomTom API key is missing",
        )

    params = {
        "point": f"{lat},{lon}",
        "key": TOMTOM_API_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(TOMTOM_TRAFFIC_URL, params=params)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail="TomTom traffic API request failed",
            )

        data = response.json()
        flow = data.get("flowSegmentData", {})

        return {
            "location": {"latitude": lat, "longitude": lon},
            "current_speed_kmh": flow.get("currentSpeed"),
            "free_flow_speed_kmh": flow.get("freeFlowSpeed"),
            "current_travel_time_seconds": flow.get("currentTravelTime"),
            "free_flow_travel_time_seconds": flow.get("freeFlowTravelTime"),
            "confidence": flow.get("confidence"),
        }

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to TomTom",
        )

# ============================================
# ROAD NETWORK API - OSM DATA
# ============================================

ROAD_NETWORK_FILES = {
    "urban_roads": URBAN_ROADS_FILE,
    "urban_nodes": DATA_DIR / "bengaluru_urban_nodes.csv",
    "rural_roads": RURAL_ROADS_FILE,
    "rural_nodes": DATA_DIR / "bengaluru_rural_nodes.csv",
}


def _validate_road_network_files():
    required_columns = {
        "urban_roads": {"osmid", "highway", "length", "geometry"},
        "rural_roads": {"osmid", "highway", "length", "geometry"},
        "urban_nodes": {"x", "y", "geometry"},
        "rural_nodes": {"x", "y", "geometry"},
    }
    schemas = {}

    for name, file_path in ROAD_NETWORK_FILES.items():
        if not file_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Road network file not found: {file_path.name}",
            )

        columns = set(pd.read_csv(file_path, nrows=0).columns)
        missing = required_columns[name] - columns
        if missing:
            missing_columns = ", ".join(sorted(missing))
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Invalid {file_path.name} schema; "
                    f"missing: {missing_columns}"
                ),
            )
        schemas[name] = sorted(columns)

    return schemas


def _parse_linestring(value):
    if not isinstance(value, str):
        return None

    match = re.fullmatch(r"\s*LINESTRING\s*\((.*)\)\s*", value)
    if not match:
        return None

    coordinates = []
    try:
        for pair in match.group(1).split(","):
            longitude, latitude = map(float, pair.split()[:2])
            if not (math.isfinite(longitude) and math.isfinite(latitude)):
                return None
            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                return None
            coordinates.append([longitude, latitude])
    except (ValueError, TypeError):
        return None

    return coordinates if len(coordinates) >= 2 else None


def _in_bounds(longitude, latitude, bounds):
    min_lat, max_lat, min_lon, max_lon = bounds
    return min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat


@app.get("/api/roads")
async def get_roads(
    min_lat: float = 12.8,
    max_lat: float = 13.2,
    min_lon: float = 77.4,
    max_lon: float = 77.8,
    road_type: str = None,
    max_features: int = 1200,
):
    try:
        if (
            min_lat >= max_lat
            or min_lon >= max_lon
            or max_lat - min_lat > 0.5
            or max_lon - min_lon > 0.5
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Provide a valid local bounding box no wider "
                    "than 0.5 degrees."
                ),
            )
        if not 1 <= max_features <= 2000:
            raise HTTPException(
                status_code=400,
                detail="max_features must be between 1 and 2000.",
            )

        schemas = _validate_road_network_files()
        bounds = (min_lat, max_lat, min_lon, max_lon)
        per_source_limit = max(1, math.ceil(max_features / 2))
        node_coordinates = set()
        node_count = 0
        features = []
        source_counts = {"urban": 0, "rural": 0}
        truncated = False

        for source in ("urban", "rural"):
            node_file = ROAD_NETWORK_FILES[f"{source}_nodes"]
            for chunk in pd.read_csv(
                node_file,
                usecols=["x", "y"],
                chunksize=20000,
            ):
                for row in chunk.itertuples(index=False):
                    try:
                        longitude = float(row.x)
                        latitude = float(row.y)
                    except (ValueError, TypeError):
                        continue
                    if _in_bounds(longitude, latitude, bounds):
                        node_coordinates.add(
                            (round(longitude, 6), round(latitude, 6))
                        )
                        node_count += 1

            roads_file = ROAD_NETWORK_FILES[f"{source}_roads"]
            road_columns = set(pd.read_csv(roads_file, nrows=0).columns)
            available_columns = (
                "osmid",
                "highway",
                "name",
                "oneway",
                "length",
                "geometry",
                "lanes",
                "maxspeed",
            )
            use_columns = [
                column
                for column in available_columns
                if column in road_columns
            ]

            for chunk in pd.read_csv(
                roads_file,
                usecols=use_columns,
                chunksize=10000,
            ):
                for row in chunk.itertuples(index=False):
                    coordinates = _parse_linestring(row.geometry)
                    if not coordinates:
                        continue

                    longitudes = [point[0] for point in coordinates]
                    latitudes = [point[1] for point in coordinates]
                    intersects = not (
                        max(longitudes) < min_lon
                        or min(longitudes) > max_lon
                        or max(latitudes) < min_lat
                        or min(latitudes) > max_lat
                    )
                    if not intersects:
                        continue

                    properties = row._asdict()
                    endpoints = (coordinates[0], coordinates[-1])
                    connected_endpoints = sum(
                        (round(point[0], 6), round(point[1], 6))
                        in node_coordinates
                        for point in endpoints
                    )
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coordinates,
                        },
                        "properties": {
                            "osmid": str(properties.get("osmid")),
                            "highway": properties.get("highway"),
                            "name": properties.get("name"),
                            "oneway": properties.get("oneway"),
                            "length": properties.get("length"),
                            "lanes": properties.get("lanes"),
                            "maxspeed": properties.get("maxspeed"),
                            "source": source,
                            "connected_endpoints": connected_endpoints,
                        },
                    })
                    source_counts[source] += 1
                    if source_counts[source] >= per_source_limit:
                        truncated = True
                        break

                if source_counts[source] >= per_source_limit:
                    break

        return {
            "type": "FeatureCollection",
            "features": clean_nan(features),
            "count": len(features),
            "truncated": truncated,
            "sources": source_counts,
            "node_count": node_count,
            "connectivity_note": (
                "Endpoint connectivity is inferred by matching road "
                "coordinates to node coordinates; road CSVs have no "
                "explicit endpoint IDs."
            ),
            "schemas_validated": schemas,
            "bbox": {
                "min_lat": min_lat,
                "max_lat": max_lat,
                "min_lon": min_lon,
                "max_lon": max_lon,
            },
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading road network: {str(error)}",
        )


# ============================================
# WEATHER API - BENGALURU
# ============================================

@app.get("/api/weather")
async def get_weather(lat: float = 12.9716, lon: float = 77.5946):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "precipitation,"
            "rain,"
            "wind_speed_10m,"
            "weather_code"
        ),
        "timezone": "auto"
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:

            response = await client.get(
                url,
                params=params
            )

            response.raise_for_status()

            data = response.json()

        current = data.get("current", {})
        units = data.get("current_units", {})

        weather_code = current.get("weather_code")

        weather_conditions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snowfall",
            73: "Moderate snowfall",
            75: "Heavy snowfall",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail"
        }

        return {
            "location": "Selected location",
            "latitude": lat,
            "longitude": lon,
            "time": current.get("time"),
            "temperature": current.get("temperature_2m"),
            "feels_like": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation"),
            "rain": current.get("rain"),
            "wind_speed": current.get("wind_speed_10m"),
            "weather_code": weather_code,
            "weather_condition": weather_conditions.get(
                weather_code,
                "Unknown"
            ),
            "units": {
                "temperature": units.get("temperature_2m"),
                "feels_like": units.get("apparent_temperature"),
                "humidity": units.get("relative_humidity_2m"),
                "precipitation": units.get("precipitation"),
                "rain": units.get("rain"),
                "wind_speed": units.get("wind_speed_10m")
            }
        }

    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Weather API error: {str(exc)}"
        )
# --------------------------------------------------
# RUN SERVER
# --------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
    )
