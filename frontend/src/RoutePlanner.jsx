import { useCallback, useEffect, useRef, useState } from "react";

import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
  useMapEvents,
} from "react-leaflet";

import L from "leaflet";
import "leaflet/dist/leaflet.css";

import "./RoutePlanner.css";
import CameraCapture from "./CameraCapture";
import TripSummary from "./TripSummary";
import TrafficSignRecognition from "./TrafficSignRecognition";
import TrafficCard from "./TrafficCard";
import WeatherCard from "./WeatherCard";

// Fix Leaflet marker icons
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl:
    "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

// The bundled OSM road files cover Bengaluru; the basemap and search are global.
const DEFAULT_CENTER = [12.9716, 77.5946];
const API_BASE_URL = "http://127.0.0.1:8001";

const ROUTE_COLORS = ["#2563eb", "#f59e0b", "#9333ea"];

// Format distance
const formatDistance = (meters) => {
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)} km`;
  }

  return `${Math.round(meters)} m`;
};

// Format duration
const formatDuration = (seconds) => {
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours > 0) {
    return `${hours} hr ${minutes} min`;
  }

  return `${minutes} min`;
};

const calculateDistance = (lat1, lon1, lat2, lon2) => {
  const radius = 6371e3;
  const latitude1 = (lat1 * Math.PI) / 180;
  const latitude2 = (lat2 * Math.PI) / 180;
  const deltaLatitude = ((lat2 - lat1) * Math.PI) / 180;
  const deltaLongitude = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(deltaLatitude / 2) ** 2 +
    Math.cos(latitude1) *
      Math.cos(latitude2) *
      Math.sin(deltaLongitude / 2) ** 2;
  return radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
};

const calculateBearing = (lat1, lon1, lat2, lon2) => {
  const latitude1 = (lat1 * Math.PI) / 180;
  const latitude2 = (lat2 * Math.PI) / 180;
  const deltaLongitude = ((lon2 - lon1) * Math.PI) / 180;
  const y = Math.sin(deltaLongitude) * Math.cos(latitude2);
  const x =
    Math.cos(latitude1) * Math.sin(latitude2) -
    Math.sin(latitude1) * Math.cos(latitude2) * Math.cos(deltaLongitude);
  const bearing = (Math.atan2(y, x) * 180) / Math.PI;
  return (bearing + 360) % 360;
};

const parseSpeedLimit = (value) => {
  const match = String(value || "").match(
    /(?:Speed limit\s*\()?\s*(\d+(?:\.\d+)?)\s*(km\/h|kmh|mph)?/i
  );
  if (!match) return null;
  const speed = Number(match[1]);
  return match[2]?.toLowerCase() === "mph" ? speed * 1.60934 : speed;
};

const projectPointToSegment = (latitude, longitude, startLat, startLon, endLat, endLon) => {
  const dx = endLon - startLon;
  const dy = endLat - startLat;
  const lengthSquared = dx * dx + dy * dy;

  if (lengthSquared === 0) {
    return {
      distance: calculateDistance(latitude, longitude, startLat, startLon),
      fraction: 0,
    };
  }

  const x = longitude - startLon;
  const y = latitude - startLat;
  const fraction = Math.max(0, Math.min(1, (x * dx + y * dy) / lengthSquared));
  const projectedLat = startLat + (endLat - startLat) * fraction;
  const projectedLon = startLon + (endLon - startLon) * fraction;

  return {
    distance: calculateDistance(latitude, longitude, projectedLat, projectedLon),
    fraction,
    projectedLat,
    projectedLon,
  };
};

const distanceToRoad = (latitude, longitude, coordinates) => {
  const longitudeScale = 111320 * Math.cos((latitude * Math.PI) / 180);
  let nearest = Infinity;

  for (let index = 0; index < coordinates.length - 1; index += 1) {
    const [longitude1, latitude1] = coordinates[index];
    const [longitude2, latitude2] = coordinates[index + 1];
    const x1 = (longitude1 - longitude) * longitudeScale;
    const y1 = (latitude1 - latitude) * 110540;
    const x2 = (longitude2 - longitude) * longitudeScale;
    const y2 = (latitude2 - latitude) * 110540;
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lengthSquared = dx * dx + dy * dy;
    const fraction = lengthSquared
      ? Math.max(0, Math.min(1, -(x1 * dx + y1 * dy) / lengthSquared))
      : 0;
    nearest = Math.min(
      nearest,
      Math.hypot(x1 + fraction * dx, y1 + fraction * dy)
    );
  }

  return nearest;
};

// Map controller
function MapController({ center, zoom, routeBounds }) {
  const map = useMap();

  useEffect(() => {
    if (routeBounds) {
      map.fitBounds(routeBounds, {
        padding: [50, 50],
        maxZoom: 15,
      });
    } else if (center) {
      map.setView(center, zoom || 13);
    }
  }, [center, zoom, routeBounds, map]);

  return null;
}

function RoadNetworkLayer({ onStatus, currentLocation, onRoadContext }) {
  const map = useMap();
  const [features, setFeatures] = useState([]);
  const requestTimer = useRef(null);
  const requestController = useRef(null);

  const loadRoads = useCallback(() => {
    clearTimeout(requestTimer.current);
    requestTimer.current = setTimeout(async () => {
      const center = map.getCenter();
      if (
        center.lat < 12.75 || center.lat > 13.25 ||
        center.lng < 77.35 || center.lng > 78.05
      ) {
        requestController.current?.abort();
        setFeatures([]);
        onStatus("Local road data: Bengaluru only");
        return;
      }

      if (map.getZoom() < 11) {
        setFeatures([]);
        onStatus("Zoom in to view Bengaluru roads");
        return;
      }

      requestController.current?.abort();
      const controller = new AbortController();
      requestController.current = controller;
      const bounds = map.getBounds();
      const halfLat = Math.min((bounds.getNorth() - bounds.getSouth()) / 2, 0.24);
      const halfLon = Math.min((bounds.getEast() - bounds.getWest()) / 2, 0.24);
      const params = new URLSearchParams({
        min_lat: String(Math.max(-90, center.lat - halfLat)),
        max_lat: String(Math.min(90, center.lat + halfLat)),
        min_lon: String(Math.max(-180, center.lng - halfLon)),
        max_lon: String(Math.min(180, center.lng + halfLon)),
        max_features: "800",
      });

      onStatus("Loading Bengaluru roads");
      try {
        const response = await fetch(`${API_BASE_URL}/api/roads?${params}`, {
          signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Road network unavailable");
        }
        setFeatures(data.features || []);
        onStatus(`Bengaluru roads: ${data.count}${data.truncated ? "+" : ""}`);
      } catch (error) {
        if (error.name !== "AbortError") {
          setFeatures([]);
          onStatus("OSM roads unavailable");
        }
      }
    }, 500);
  }, [map, onStatus]);

  useMapEvents({ moveend: loadRoads, zoomend: loadRoads });

  useEffect(() => {
    loadRoads();
    return () => {
      clearTimeout(requestTimer.current);
      requestController.current?.abort();
    };
  }, [loadRoads]);

  useEffect(() => {
    if (!currentLocation || !features.length) {
      onRoadContext(null);
      return;
    }

    let nearestRoad = null;
    let nearestDistance = Infinity;
    for (const feature of features) {
      const distance = distanceToRoad(
        currentLocation.lat,
        currentLocation.lon,
        feature.geometry?.coordinates || []
      );
      if (distance < nearestDistance) {
        nearestRoad = feature.properties;
        nearestDistance = distance;
      }
    }

    onRoadContext(
      nearestDistance <= 150
        ? { ...nearestRoad, distanceMeters: nearestDistance }
        : null
    );
  }, [currentLocation, features, onRoadContext]);

  return features.map((feature, index) => {
    const properties = feature.properties || {};
    const positions = (feature.geometry?.coordinates || []).map(
      ([longitude, latitude]) => [latitude, longitude]
    );
    if (positions.length < 2) return null;

    return (
      <Polyline
        key={`${properties.source}-${properties.osmid}-${index}`}
        positions={positions}
        pathOptions={{
          color: properties.highway === "motorway" ? "#d97706" : "#64748b",
          weight: properties.highway === "motorway" ? 3 : 1.5,
          opacity: 0.65,
        }}
      >
        <Popup>
          <strong>{properties.name || "Unnamed road"}</strong>
          <br />
          {properties.highway || "Road"} · {properties.source} network
          <br />
          Node-matched endpoints: {properties.connected_endpoints}/2
        </Popup>
      </Polyline>
    );
  });
}

export default function RoutePlanner() {
  const mapRef = useRef(null);
  const lastTripLocationRef = useRef(null);
  const lastSpokenWarningRef = useRef({ signature: "", timestamp: 0 });

  const [start, setStart] = useState("");
  const [destination, setDestination] = useState("");

  const [startCoords, setStartCoords] = useState(null);
  const [destinationCoords, setDestinationCoords] = useState(null);

  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(0);

  const [loading, setLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);

  const [error, setError] = useState("");

  const [mapCenter, setMapCenter] = useState(DEFAULT_CENTER);
  const [mapZoom, setMapZoom] = useState(12);
  const [mapStyle, setMapStyle] = useState("standard");
  const [routePanelOpen, setRoutePanelOpen] = useState(true);
  const [showRoadNetwork, setShowRoadNetwork] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [routeBounds, setRouteBounds] = useState(null);
  const [activeLocationName, setActiveLocationName] = useState("Bengaluru, Karnataka");
  const [trafficContext, setTrafficContext] = useState(null);
  const [weatherContext, setWeatherContext] = useState(null);
  const [roadContext, setRoadContext] = useState(null);

  // Trip state management
  const [tripStatus, setTripStatus] = useState("inactive"); // inactive, in_progress, completed
  const [tripData, setTripData] = useState({
    startTime: null,
    endTime: null,
    distanceTraveled: 0,
    roadDamageDetections: [],
    trafficSignsDetected: [],
    currentLocation: null,
    currentHeading: 0,
  });

  // Accident hotspot data
  const [hotspots, setHotspots] = useState([]);
  const [roadNetworkStatus, setRoadNetworkStatus] = useState("Loading Bengaluru roads");

  // Current location marker
  const currentLocationIcon = L.divIcon({
    className: "current-location-marker",
    html: '<div class="location-dot"></div>',
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });

  const navigationMarkerIcon = (heading = 0) =>
    L.divIcon({
      className: "current-location-marker is-navigation",
      html: `<div class="location-triangle" style="--heading:${heading}deg"></div>`,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    });

  // Accident hotspot marker icon
  const hotspotIcon = L.divIcon({
    className: "hotspot-marker",
    html: '<div class="hotspot-dot"></div>',
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });

  const handleRoadContext = useCallback((road) => {
    setRoadContext(road);
  }, []);

  const handleTrafficUpdate = useCallback((traffic, locationKey) => {
    setTrafficContext(traffic ? { data: traffic, locationKey } : null);
  }, []);

  const handleWeatherUpdate = useCallback((weather, locationKey) => {
    setWeatherContext(weather ? { data: weather, locationKey } : null);
  }, []);

  // Fetch accident hotspots
  useEffect(() => {
    const fetchHotspots = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/hotspots`);
        if (response.ok) {
          const data = await response.json();
          console.log("Hotspots data received:", data.length, "records");
          setHotspots(data);
        } else {
          console.error("Failed to fetch hotspots:", response.status, response.statusText);
        }
      } catch (err) {
        console.error("Failed to fetch hotspots:", err);
      } finally {
      }
    };

    fetchHotspots();
  }, []);

  // Geocode a location
  const geocodeLocation = async (place) => {
    const query = place.trim();

    if (!query) {
      throw new Error("Please enter a location.");
    }

    // Accept latitude, longitude directly
    const coordinateMatch = query.match(
      /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/
    );

    if (coordinateMatch) {
      const lat = Number(coordinateMatch[1]);
      const lon = Number(coordinateMatch[2]);

      if (
        lat >= -90 &&
        lat <= 90 &&
        lon >= -180 &&
        lon <= 180
      ) {
        return {
          lat,
          lon,
          display_name: query,
        };
      }

      throw new Error("Invalid latitude or longitude.");
    }

    const response = await fetch(
      `${API_BASE_URL}/api/geocode?query=${encodeURIComponent(query)}`
    );

    if (!response.ok) {
      throw new Error("Unable to search for this location.");
    }

    const data = await response.json();

    if (!data.locations?.length) {
      throw new Error(`Location not found: ${query}`);
    }

    return data.locations[0];
  };

  // Use current GPS location
  const useCurrentLocation = () => {
    setError("");

    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }

    setLocationLoading(true);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;

        const coords = {
          lat: latitude,
          lon: longitude,
        };

        setStartCoords(coords);
        setActiveLocationName("Current location");

        setStart(
          `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`
        );

        setMapCenter([latitude, longitude]);
        setMapZoom(16);
        setRouteBounds(null);
        setRoadNetworkStatus("Loading Bengaluru roads");

        setRoutes([]);
        setSelectedRoute(0);

        setLocationLoading(false);

        if (mapRef.current) {
          mapRef.current.setView(
            [latitude, longitude],
            16
          );
        }
      },
      (err) => {
        let message = "Unable to access your current location.";

        if (err.code === 1) {
          message =
            "Location permission denied. Please allow location access.";
        } else if (err.code === 2) {
          message = "Your current location is unavailable.";
        } else if (err.code === 3) {
          message = "Location request timed out. Please try again.";
        }

        setError(message);
        setLocationLoading(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0,
      }
    );
  };

  // Find routes
  const findRoutes = async (event) => {
    event.preventDefault();

    setError("");
    setRoutes([]);
    setRouteBounds(null);
    setSelectedRoute(0);

    if (!start.trim() || !destination.trim()) {
      setError(
        "Please enter both starting point and destination."
      );
      return;
    }

    setLoading(true);

    try {
      const startLocation = startCoords
        ? startCoords
        : await geocodeLocation(start);

      const destinationLocation = destinationCoords
        ? destinationCoords
        : await geocodeLocation(destination);

      setStartCoords(startLocation);
      setDestinationCoords(destinationLocation);
      setActiveLocationName(
        startLocation.display_name?.split(",").slice(0, 2).join(",") ||
          "Selected location"
      );

      const coordinates = `${startLocation.lon},${startLocation.lat};${destinationLocation.lon},${destinationLocation.lat}`;

      const url =
        `https://router.project-osrm.org/route/v1/driving/${coordinates}` +
        "?overview=full&geometries=geojson&alternatives=true&steps=true";

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error("Unable to calculate routes.");
      }

      const data = await response.json();

      if (data.code !== "Ok" || !data.routes?.length) {
        throw new Error(
          "No route found. Try different locations."
        );
      }

      const formattedRoutes = data.routes.map(
        (route, index) => ({
          id: index,
          distance: route.distance,
          duration: route.duration,
          geometry: route.geometry.coordinates.map(
            ([lon, lat]) => [lat, lon]
          ),
          color:
            ROUTE_COLORS[index % ROUTE_COLORS.length],
          steps:
            route.legs?.flatMap(
              (leg) => leg.steps || []
            ) || [],
        })
      );

      setRoutes(formattedRoutes);
      setSelectedRoute(0);

      const bounds = L.latLngBounds(
        formattedRoutes[0].geometry
      );

      setRouteBounds(bounds);

      setMapCenter([
        startLocation.lat,
        startLocation.lon,
      ]);

      setMapZoom(13);
      setRoadNetworkStatus("Loading map data");
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  // Select a route
  const selectRoute = (index) => {
    setSelectedRoute(index);

    const route = routes[index];

    if (route) {
      setRouteBounds(
        L.latLngBounds(route.geometry)
      );
    }
  };

  const swapLocations = () => {
    setStart(destination);
    setDestination(start);
    setStartCoords(destinationCoords);
    setDestinationCoords(startCoords);
    setRoutes([]);
    setSelectedRoute(0);
    setRouteBounds(null);
    setError("");
  };

  // Clear route
  const clearRoute = () => {
    setStart("");
    setDestination("");
    setActiveLocationName("Bengaluru, Karnataka");

    setStartCoords(null);
    setDestinationCoords(null);

    setRoutes([]);
    setSelectedRoute(0);

    setError("");
    setRouteBounds(null);

    setMapCenter(DEFAULT_CENTER);
    setMapZoom(12);

    // Reset trip state
    setTripStatus("inactive");
    setTripData({
      startTime: null,
      endTime: null,
      distanceTraveled: 0,
      currentSpeedKmh: null,
      roadDamageDetections: [],
      trafficSignsDetected: [],
      currentLocation: null,
      currentHeading: 0,
    });
  };

  // Start trip
  const startTrip = () => {
    if (!selected) {
      setError("Please select a route before starting the trip.");
      return;
    }

    setTripStatus("in_progress");
    setTripData({
      startTime: new Date(),
      endTime: null,
      distanceTraveled: 0,
      roadDamageDetections: [],
      trafficSignsDetected: [],
      currentLocation: null,
      currentHeading: 0,
    });
    lastTripLocationRef.current = null;

    setError("");
  };

  // End trip
  const endTrip = () => {
    setTripStatus("completed");
    setTripData((prev) => ({
      ...prev,
      endTime: new Date(),
    }));
  };

  // Start new trip
  const startNewTrip = () => {
    setTripStatus("inactive");
    lastTripLocationRef.current = null;
    setTripData({
      startTime: null,
      endTime: null,
      distanceTraveled: 0,
      roadDamageDetections: [],
      trafficSignsDetected: [],
      currentLocation: null,
      currentHeading: 0,
    });
  };

  // Handle road damage detection from camera
  const handleRoadDamageDetection = (detection) => {
    if (tripStatus === "in_progress") {
      setTripData((prev) => ({
        ...prev,
        roadDamageDetections: [
          ...prev.roadDamageDetections,
          {
            ...detection,
            timestamp: new Date(),
            location: tripData.currentLocation,
          },
        ],
      }));
    }
  };

  // Handle traffic sign detection from camera
  const handleTrafficSignDetection = (sign) => {
    if (tripStatus === "in_progress") {
      setTripData((prev) => ({
        ...prev,
        trafficSignsDetected: [
          ...prev.trafficSignsDetected,
          {
            ...sign,
            timestamp: new Date(),
            location: tripData.currentLocation,
          },
        ],
      }));
    }
  };

  // GPS tracking during trip
  useEffect(() => {
    let watchId = null;

    if (tripStatus === "in_progress" && navigator.geolocation) {
      watchId = navigator.geolocation.watchPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          const coords = {
            lat: latitude,
            lon: longitude,
            accuracy: position.coords.accuracy,
            timestamp: position.timestamp,
          };
          const previousLocation = lastTripLocationRef.current;
          lastTripLocationRef.current = {
            ...coords,
            timestamp: position.timestamp,
          };
          const measuredSpeed = Number.isFinite(position.coords.speed)
            ? position.coords.speed * 3.6
            : null;
          const elapsedSeconds = previousLocation
            ? (position.timestamp - previousLocation.timestamp) / 1000
            : 0;
          const estimatedSpeed =
            previousLocation &&
            coords.accuracy <= 40 &&
            previousLocation.accuracy <= 40 &&
            elapsedSeconds >= 1
              ? (calculateDistance(
                  previousLocation.lat,
                  previousLocation.lon,
                  latitude,
                  longitude
                ) *
                  3.6) /
                elapsedSeconds
              : null;
          const speedKmh = measuredSpeed ?? estimatedSpeed;
          const headingDegrees = Number.isFinite(position.coords.heading)
            ? position.coords.heading
            : previousLocation
              ? calculateBearing(
                  previousLocation.lat,
                  previousLocation.lon,
                  latitude,
                  longitude
                )
              : 0;

          setTripData((prev) => ({
            ...prev,
            currentLocation: coords,
            currentSpeedKmh: speedKmh,
            currentHeading: headingDegrees,
            distanceTraveled: prev.distanceTraveled + (
              previousLocation
                ? calculateDistance(
                    previousLocation.lat,
                    previousLocation.lon,
                    latitude,
                    longitude
                  )
                : 0
            ),
          }));

          // Update map center to follow user
          if (mapRef.current) {
            const mapCenter = mapRef.current.getCenter();
            if (
              calculateDistance(
                mapCenter.lat,
                mapCenter.lng,
                latitude,
                longitude
              ) >= 150
            ) {
              mapRef.current.setView([latitude, longitude], 16);
            }
          }

        },
        (err) => {
          console.error("GPS tracking error:", err.message || err.code || err);
          setError("Trip is active, but GPS tracking is unavailable. Check location permission.");
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 5000,
        }
      );
    }

    return () => {
      if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
      }
    };
  }, [tripStatus]);

  const gpsTimestamp = tripData.currentLocation?.timestamp || 0;
  const recentDamage = [...tripData.roadDamageDetections]
    .reverse()
    .find((detection) => gpsTimestamp - new Date(detection.timestamp).getTime() < 120000);
  const recentSign = [...tripData.trafficSignsDetected]
    .reverse()
    .find((sign) => gpsTimestamp - new Date(sign.timestamp).getTime() < 120000);
  const signName = recentSign?.sign_name || "";
  const signSpeedLimit = /^Speed limit\s*\(/i.test(signName)
    ? parseSpeedLimit(signName)
    : null;
  const roadSpeedLimit = parseSpeedLimit(roadContext?.maxspeed);
  const postedSpeedLimit = signSpeedLimit ?? roadSpeedLimit;
  const currentSpeedKmh = tripData.currentSpeedKmh;
  const contextLocation = tripData.currentLocation || startCoords;
  const contextLocationKey = contextLocation
    ? `${Number(Number(contextLocation.lat).toFixed(2))},${Number(Number(contextLocation.lon).toFixed(2))}`
    : null;
  const currentWeatherContext =
    weatherContext?.locationKey === contextLocationKey
      ? weatherContext.data
      : null;
  const currentTrafficContext =
    trafficContext?.locationKey === contextLocationKey
      ? trafficContext.data
      : null;
  const cautionReasons = [];
  let cautionThreshold = 60;

  const weatherCode = currentWeatherContext?.weather_code;
  const wetOrPoorWeather =
    Number(currentWeatherContext?.rain) > 0 ||
    Number(currentWeatherContext?.precipitation) >= 0.2 ||
    [45, 48, 51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99].includes(weatherCode);
  if (wetOrPoorWeather) {
    cautionThreshold = Math.min(cautionThreshold, 45);
    cautionReasons.push(`weather: ${currentWeatherContext?.weather_condition || "wet or low-visibility conditions"}`);
  }

  const trafficReduction = currentTrafficContext?.free_flow_speed_kmh
    ? (currentTrafficContext.free_flow_speed_kmh - currentTrafficContext.current_speed_kmh) /
      currentTrafficContext.free_flow_speed_kmh
    : 0;
  if (trafficReduction >= 0.3) {
    cautionThreshold = Math.min(cautionThreshold, 45);
    cautionReasons.push("heavy traffic nearby");
  }

  if (recentDamage) {
    cautionThreshold = Math.min(cautionThreshold, 35);
    cautionReasons.push(`recent road damage: ${recentDamage.class_name || "hazard"}`);
  }

  if (recentSign) {
    if (signSpeedLimit != null && currentSpeedKmh > signSpeedLimit) {
      cautionReasons.push(`recognized ${signName}`);
    }
    if (/stop|yield|traffic signals|pedestrian|children crossing|slippery|bumpy|road work|general caution/i.test(signName)) {
      cautionThreshold = Math.min(cautionThreshold, 25);
      cautionReasons.push(`recognized sign: ${signName}`);
    }
  }

  const roadType = String(roadContext?.highway || "").toLowerCase();
  if (/residential|service|living_street|unclassified|track/.test(roadType)) {
    cautionThreshold = Math.min(cautionThreshold, 40);
    cautionReasons.push(`local road structure: ${roadType.replaceAll("_", " ")}`);
  }
  const roadLanes = Number.parseInt(roadContext?.lanes, 10);
  if (Number.isFinite(roadLanes) && roadLanes <= 1) {
    cautionThreshold = Math.min(cautionThreshold, 40);
    cautionReasons.push("narrow road structure");
  }
  if (roadSpeedLimit != null) {
    cautionThreshold = Math.min(cautionThreshold, roadSpeedLimit);
    cautionReasons.push(`OSM posted speed: ${Math.round(roadSpeedLimit)} km/h`);
  }

  const speedIsHigh =
    currentSpeedKmh != null &&
    currentSpeedKmh > 0 &&
    (currentSpeedKmh >= cautionThreshold ||
      (postedSpeedLimit != null && currentSpeedKmh > postedSpeedLimit));
  if (speedIsHigh && cautionReasons.length === 0) {
    cautionReasons.push("speed is high for the current trip");
  }
  const speedAdvisory = speedIsHigh
    ? {
        speed: Math.round(currentSpeedKmh),
        reasons: cautionReasons,
        signature: cautionReasons.join("|") || "high-speed",
      }
    : null;
  const advisorySignature = speedAdvisory?.signature;
  const advisorySpeed = speedAdvisory?.speed;
  const advisoryReasons = speedAdvisory?.reasons.join(". ") || "";

  useEffect(() => {
    if (
      tripStatus !== "in_progress" ||
      !advisorySignature ||
      !window.speechSynthesis
    ) {
      return;
    }

    const warningTimestamp = gpsTimestamp;
    const previous = lastSpokenWarningRef.current;
    if (
      previous.signature === advisorySignature &&
      warningTimestamp - previous.timestamp < 25000
    ) {
      return;
    }

    const warning = new SpeechSynthesisUtterance(
      `Reduce your speed. Current speed ${advisorySpeed} kilometers per hour. ${advisoryReasons}. Follow the posted speed limit and traffic signals.`
    );
    warning.rate = 1;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(warning);
    lastSpokenWarningRef.current = {
      signature: advisorySignature,
      timestamp: warningTimestamp,
    };
  }, [advisorySignature, advisorySpeed, advisoryReasons, gpsTimestamp, tripStatus]);

  // Calculate remaining distance on route
  const calculateRemainingDistance = (currentCoords, routeGeometry) => {
    if (!currentCoords || !routeGeometry || routeGeometry.length === 0) {
      return null;
    }

    let nearestDistance = Infinity;
    let nearestIndex = 0;
    let nearestFraction = 0;

    for (let index = 0; index < routeGeometry.length - 1; index += 1) {
      const [startLat, startLon] = routeGeometry[index];
      const [endLat, endLon] = routeGeometry[index + 1];
      const projection = projectPointToSegment(
        currentCoords.lat,
        currentCoords.lon,
        startLat,
        startLon,
        endLat,
        endLon
      );

      if (projection.distance < nearestDistance) {
        nearestDistance = projection.distance;
        nearestIndex = index;
        nearestFraction = projection.fraction;
      }
    }

    if (!Number.isFinite(nearestDistance)) {
      return null;
    }

    let remainingDistance = 0;

    for (let index = nearestIndex + 1; index < routeGeometry.length - 1; index += 1) {
      const [segmentStartLat, segmentStartLon] = routeGeometry[index];
      const [segmentEndLat, segmentEndLon] = routeGeometry[index + 1];
      remainingDistance += calculateDistance(
        segmentStartLat,
        segmentStartLon,
        segmentEndLat,
        segmentEndLon
      );
    }

    const [segmentStartLat, segmentStartLon] = routeGeometry[nearestIndex];
    const [segmentEndLat, segmentEndLon] = routeGeometry[nearestIndex + 1];
    const segmentLength = calculateDistance(
      segmentStartLat,
      segmentStartLon,
      segmentEndLat,
      segmentEndLon
    );

    remainingDistance += segmentLength * (1 - nearestFraction);
    return remainingDistance;
  };

  const calculateNearestRouteDistance = (currentCoords, routeGeometry) => {
    if (!currentCoords || !routeGeometry || routeGeometry.length === 0) {
      return Infinity;
    }

    let nearestDistance = Infinity;

    for (let index = 0; index < routeGeometry.length - 1; index += 1) {
      const [startLat, startLon] = routeGeometry[index];
      const [endLat, endLon] = routeGeometry[index + 1];
      const projection = projectPointToSegment(
        currentCoords.lat,
        currentCoords.lon,
        startLat,
        startLon,
        endLat,
        endLon
      );
      nearestDistance = Math.min(nearestDistance, projection.distance);
    }

    return nearestDistance;
  };

  const selected = routes[selectedRoute];
  const routeDeviation =
    tripStatus === "in_progress" && tripData.currentLocation && selected
      ? calculateNearestRouteDistance(
          tripData.currentLocation,
          selected.geometry
        ) > 60
      : false;

  const remainingDistanceOnRoute =
    tripStatus === "in_progress" && tripData.currentLocation && selected
      ? calculateRemainingDistance(
          tripData.currentLocation,
          selected.geometry
        )
      : null;
  const headingText = Number.isFinite(tripData.currentHeading)
    ? `${Math.round(tripData.currentHeading)}°`
    : "--";
  const etaSeconds =
    tripStatus === "in_progress" &&
    currentSpeedKmh != null &&
    currentSpeedKmh > 0 &&
    remainingDistanceOnRoute != null &&
    remainingDistanceOnRoute > 0
      ? Math.max(0, remainingDistanceOnRoute / (currentSpeedKmh / 3.6))
      : null;
  const contextLocationName = tripData.currentLocation
    ? "Current location"
    : startCoords
      ? activeLocationName
      : "";
  const recenterOnCurrentLocation = () => {
    if (!tripData.currentLocation || !mapRef.current) return;
    mapRef.current.setView(
      [tripData.currentLocation.lat, tripData.currentLocation.lon],
      Math.max(mapRef.current.getZoom(), 16),
      { animate: true }
    );
  };

  return (
    <div className="route-planner">

      {/* Sidebar */}
      <aside className={`route-sidebar ${routePanelOpen ? "" : "is-collapsed"}`}>

        {/* Header */}
        <div className="route-header">
          <div className="route-logo">🗺️</div>

          <div>
            <h1>RoadSafe Navigator</h1>
            <p>Global map · Bengaluru risk data</p>
          </div>
        </div>

        <div className="route-section-heading">
          <h2>Directions</h2>
          <span>Driving</span>
        </div>

        {/* Route Search */}
        <form
          className="route-form"
          onSubmit={findRoutes}
        >
          <label htmlFor="start">
            Starting Point
          </label>

          <input
            id="start"
            type="text"
            placeholder="Enter starting location"
            value={start}
            onChange={(e) => {
              setStart(e.target.value);
              setStartCoords(null);
            }}
          />

          <button
            type="button"
            className="location-button"
            onClick={useCurrentLocation}
            disabled={locationLoading}
          >
            {locationLoading
              ? "📍 Detecting Location..."
              : "📍 Use My Current Location"}
          </button>

          <button
            type="button"
            className="swap-locations-button"
            onClick={swapLocations}
            disabled={!start && !destination}
            aria-label="Swap starting point and destination"
            title="Swap starting point and destination"
          >
            <span aria-hidden="true">↕</span>
            Swap route
          </button>

          <label htmlFor="destination">
            Destination
          </label>

          <input
            id="destination"
            type="text"
            placeholder="Enter destination"
            value={destination}
            onChange={(e) => {
              setDestination(e.target.value);
              setDestinationCoords(null);
            }}
          />

          <button
            type="submit"
            className="find-route-button"
            disabled={loading}
          >
            {loading
              ? "Finding Routes..."
              : "🔍 Find Routes"}
          </button>

          <button
            type="button"
            className="clear-button"
            onClick={clearRoute}
          >
            Clear Route
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="route-error">
            {error}
          </div>
        )}

        {/* Route Results */}
        {routes.length > 0 && (
          <div className="route-results">
            <h2>Available Routes</h2>

            <p className="route-disclaimer">
              These are driving routes. Accident risk
              has not been evaluated.
            </p>

            {routes.map((route, index) => (
              <button
                type="button"
                key={route.id}
                className={`route-card ${
                  selectedRoute === index
                    ? "active"
                    : ""
                }`}
                onClick={() => selectRoute(index)}
              >
                <div className="route-card-heading">
                  <span
                    className="route-color"
                    style={{
                      backgroundColor: route.color,
                    }}
                  />

                  <div className="route-card-copy">
                    <strong>
                      {index === 0 ? "Fastest route" : `Alternative ${index + 1}`}
                    </strong>
                    <small>{index === 0 ? "Recommended" : "Alternate path"}</small>
                  </div>
                </div>

                <div className="route-details">
                  <span>
                    {formatDistance(route.distance)}
                  </span>

                  <span>
                    {formatDuration(route.duration)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Selected Route */}
        {selected && tripStatus === "inactive" && (
          <div className="selected-route">
            <h3>Selected Route</h3>

            <div className="selected-route-stat">
              <span>Distance</span>
              <strong>
                {formatDistance(selected.distance)}
              </strong>
            </div>

            <div className="selected-route-stat">
              <span>Estimated time</span>
              <strong>
                {formatDuration(selected.duration)}
              </strong>
            </div>

            <div className="risk-notice">
              <span className="risk-indicator" />

              <div>
                <strong>
                  Bengaluru safety context
                </strong>

                <p>
                  Route ranking uses driving directions, not accident risk. Safety tools show historical police-station hotspots and live camera, traffic, and weather context.
                </p>
              </div>
            </div>

            <button
              type="button"
              className="start-trip-button"
              onClick={startTrip}
            >
              🚀 Start Trip
            </button>
          </div>
        )}

        {/* Trip In Progress */}
        {tripStatus === "in_progress" && (
          <div className="trip-active">
            <div className="trip-status-header">
              <span className="trip-status-dot in-progress" />
              <h3>Trip In Progress</h3>
            </div>

            <div className="live-speed">
              <span>GPS speed</span>
              <strong>
                {tripData.currentSpeedKmh == null
                  ? "Waiting for GPS"
                  : `${tripData.currentSpeedKmh.toFixed(0)} km/h`}
              </strong>
            </div>

            {speedAdvisory && (
              <div className="speed-advisory" role="alert" aria-live="assertive">
                <strong>Reduce speed now</strong>
                <span>
                  Current speed: {speedAdvisory.speed} km/h. {speedAdvisory.reasons.join(" · ")}
                </span>
                <small>
                  Caution thresholds are not legal limits. The camera locates sign regions but does not read sign meaning or live signal phases; obey posted limits and actual signals.
                </small>
              </div>
            )}

            <div className="trip-stats">
              <div className="trip-stat">
                <span>Distance Traveled</span>
                <strong>
                  {formatDistance(tripData.distanceTraveled)}
                </strong>
              </div>

              <div className="trip-stat">
                <span>Remaining Distance</span>
                <strong>
                  {tripData.currentLocation && selected
                    ? formatDistance(
                        calculateRemainingDistance(
                          tripData.currentLocation,
                          selected.geometry
                        )
                      )
                    : formatDistance(selected?.distance || 0)}
                </strong>
              </div>

              <div className="trip-stat">
                <span>Elapsed Time</span>
                <strong>
                  {tripData.startTime
                    ? formatDuration(
                        Math.floor(
                          (new Date() - new Date(tripData.startTime)) / 1000
                        )
                      )
                    : "0 min"}
                </strong>
              </div>

              <div className="trip-stat">
                <span>Damage Detections</span>
                <strong>
                  {tripData.roadDamageDetections.length}
                </strong>
              </div>

              <div className="trip-stat">
                <span>Confirmed Sign Regions</span>
                <strong>
                  {tripData.trafficSignsDetected.length}
                </strong>
              </div>
            </div>

            <button
              type="button"
              className="end-trip-button"
              onClick={endTrip}
            >
              🛑 End Trip
            </button>
          </div>
        )}

        <details
          className="map-tools-panel"
          open={tripStatus === "in_progress"}
        >
          <summary>Road safety tools</summary>
          <CameraCapture
            tripStatus={tripStatus}
            onRoadDamageDetection={handleRoadDamageDetection}
            onTrafficSignDetection={handleTrafficSignDetection}
          />

          {tripStatus === "in_progress" && (
            <TrafficSignRecognition detectedSigns={tripData.trafficSignsDetected} />
          )}
        </details>

        {/* Traffic and Weather Cards */}
        <details className="map-tools-panel">
          <summary>Live traffic and weather</summary>
          <div className="environmental-info">
            <TrafficCard
              location={contextLocation}
              locationName={contextLocationName}
              onTrafficUpdate={handleTrafficUpdate}
            />
            <WeatherCard
              location={contextLocation}
              locationName={contextLocationName}
              onWeatherUpdate={handleWeatherUpdate}
            />
          </div>
        </details>

        {/* Trip Summary */}
        {tripStatus === "completed" && (
          <TripSummary
            tripData={tripData}
            startLocation={start}
            destination={destination}
            routeDistance={selected?.distance}
            onStartNewTrip={startNewTrip}
          />
        )}

        {/* Footer */}
        <div className="route-footer">
          <p>
            Worldwide map © OpenStreetMap contributors
          </p>

          <p>
            Detailed road and historical risk data currently cover Bengaluru.
          </p>
        </div>
      </aside>

      <nav className="map-quick-rail" aria-label="Map shortcuts">
        <button
          type="button"
          onClick={() => setRoutePanelOpen((open) => !open)}
          aria-label={routePanelOpen ? "Hide directions panel" : "Show directions panel"}
          aria-expanded={routePanelOpen}
          title={routePanelOpen ? "Hide directions panel" : "Show directions panel"}
        >
          <span aria-hidden="true">☰</span>
        </button>
        <button
          type="button"
          onClick={useCurrentLocation}
          disabled={locationLoading}
          aria-label="Use current location"
          title="Use current location"
        >
          <span aria-hidden="true">◎</span>
        </button>
        <button
          type="button"
          className={showHotspots ? "active" : ""}
          onClick={() => setShowHotspots((visible) => !visible)}
          aria-label={showHotspots ? "Hide accident hotspots" : "Show accident hotspots"}
          aria-pressed={showHotspots}
          title={showHotspots ? "Hide accident hotspots" : "Show accident hotspots"}
        >
          <span aria-hidden="true">⚠</span>
        </button>
      </nav>

      {/* Map */}
      <main className="route-map-container">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={12}
          className="route-map"
          whenReady={(event) => {
            mapRef.current = event.target;
          }}
        >
          <MapController
            center={mapCenter}
            zoom={mapZoom}
            routeBounds={routeBounds}
          />

          <TileLayer
            attribution={
              mapStyle === "satellite"
                ? '&copy; <a href="https://www.esri.com/">Esri</a> contributors'
                : '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }
            url={
              mapStyle === "satellite"
                ? "https://server.arcgison.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            }
          />

          {/* Starting Point */}
          {startCoords && (
            <Marker
              position={[
                startCoords.lat,
                startCoords.lon,
              ]}
              icon={currentLocationIcon}
            >
              <Popup>Starting Point</Popup>
            </Marker>
          )}

          {tripStatus === "in_progress" && tripData.currentLocation && (
            <Marker
              position={[tripData.currentLocation.lat, tripData.currentLocation.lon]}
              icon={navigationMarkerIcon(tripData.currentHeading || 0)}
            >
              <Popup>Current GPS location</Popup>
            </Marker>
          )}

          {/* Destination */}
          {destinationCoords && (
            <Marker
              position={[
                destinationCoords.lat,
                destinationCoords.lon,
              ]}
            >
              <Popup>Destination</Popup>
            </Marker>
          )}

          {/* Route Lines */}
          {routes.map((route, index) => (
            <Polyline
              key={route.id}
              positions={route.geometry}
              pathOptions={{
                color: route.color,
                weight:
                  selectedRoute === index ? 7 : 4,
                opacity:
                  selectedRoute === index ? 0.95 : 0.55,
              }}
              eventHandlers={{
                click: () => selectRoute(index),
              }}
            />
          ))}

          {showRoadNetwork && (
            <RoadNetworkLayer
              onStatus={setRoadNetworkStatus}
              currentLocation={tripData.currentLocation}
              onRoadContext={handleRoadContext}
            />
          )}

          {showHotspots && hotspots.map((hotspot, index) => {
            // Check if hotspot has coordinates
            if (hotspot.latitude && hotspot.longitude) {
              return (
                <Marker
                  key={`hotspot-${index}`}
                  position={[hotspot.latitude, hotspot.longitude]}
                  icon={hotspotIcon}
                >
                  <Popup>
                    <div className="hotspot-popup">
                      <strong>Accident Hotspot</strong>
                      <p>
                        <strong>Zone:</strong> {hotspot.Zone || hotspot.zone || "Unknown"}
                      </p>
                      <p>
                        <strong>Police Station:</strong> {hotspot.Station || hotspot.station || "Unknown"}
                      </p>
                      <p>
                        <strong>Total Accidents:</strong> {hotspot.Total_Accidents || hotspot.total_accidents || "N/A"}
                      </p>
                      <p>
                        <strong>Fatal Accidents:</strong> {hotspot.Fatal_Accidents || hotspot.fatal_accidents || "N/A"}
                      </p>
                      <p>
                        <strong>Risk Category:</strong> {hotspot.Accident_Rate_Category || hotspot.accident_rate_category || "Not specified"}
                      </p>
                      <small className="hotspot-disclaimer">
                        Historical data based on police station records. These are police station locations, not exact accident sites.
                      </small>
                    </div>
                  </Popup>
                </Marker>
              );
            }
            return null;
          })}
        </MapContainer>

        <div className="map-overlay">
          <div className="map-status-pill">
            <span className="map-status-dot" />
            <span>{roadNetworkStatus}</span>
          </div>

          <div className="map-controls-panel" aria-label="Map layers controls">
            <div className="map-floating-toolbar">
              <button
                type="button"
                className={mapStyle === "standard" ? "active" : ""}
                onClick={() => setMapStyle("standard")}
                aria-pressed={mapStyle === "standard"}
              >
                Map
              </button>
              <button
                type="button"
                className={mapStyle === "satellite" ? "active" : ""}
                onClick={() => setMapStyle("satellite")}
                aria-pressed={mapStyle === "satellite"}
              >
                Satellite
              </button>
              <button
                type="button"
                className={showRoadNetwork ? "active" : ""}
                onClick={() => setShowRoadNetwork((prev) => !prev)}
                aria-pressed={showRoadNetwork}
              >
                Roads
              </button>
              <button
                type="button"
                className={showHotspots ? "active" : ""}
                onClick={() => setShowHotspots((prev) => !prev)}
                aria-pressed={showHotspots}
              >
                Hotspots
              </button>
            </div>
          </div>

          {tripStatus === "in_progress" && (
            <>
              <button
                type="button"
                className="map-recenter-button"
                onClick={recenterOnCurrentLocation}
                disabled={!tripData.currentLocation}
                aria-label="Center map on current GPS location"
                title={tripData.currentLocation ? "Center map on my location" : "Waiting for GPS location"}
              >
                <span aria-hidden="true">◎</span>
                {tripData.currentLocation ? "Center on me" : "Waiting for GPS"}
              </button>

              <div className="live-tracker-card" aria-live="polite">
                <div className="tracker-header">
                  <span className="tracker-live-dot" />
                  <span>Live tracker</span>
                </div>

                <div className="tracker-grid">
                  <div className="tracker-box">
                    <span>Speed</span>
                    <strong>
                      {tripData.currentSpeedKmh == null
                        ? "--"
                        : `${tripData.currentSpeedKmh.toFixed(0)} km/h`}
                    </strong>
                  </div>

                  <div className="tracker-box">
                    <span>Heading</span>
                    <strong>{headingText}</strong>
                  </div>

                  <div className="tracker-box">
                    <span>Remaining</span>
                    <strong>
                      {remainingDistanceOnRoute == null
                        ? (selected ? formatDistance(selected.distance) : "--")
                        : formatDistance(remainingDistanceOnRoute)}
                    </strong>
                  </div>

                  <div className="tracker-box">
                    <span>ETA</span>
                    <strong>
                      {etaSeconds == null
                        ? "--"
                        : formatDuration(Math.max(0, Math.round(etaSeconds)))}
                    </strong>
                  </div>
                </div>
              </div>

              {routeDeviation && (
                <div className="route-warning-card" role="alert">
                  <strong>Route deviation</strong>
                  <span>
                    You are more than 60 m from the selected route. Check your position before continuing.
                  </span>
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}