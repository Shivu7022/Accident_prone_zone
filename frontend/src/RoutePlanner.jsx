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
import TrafficCard from "./TrafficCard";
import WeatherCard from "./WeatherCard";
import SpeedRecommendation from "./SpeedRecommendation";
import SearchPanel from "./SearchPanel";
import TurnByTurnBanner from "./TurnByTurnBanner";
import NavigationControls from "./NavigationControls";
import NavigationStatsBar from "./NavigationStatsBar";
import MLDetectionHUD from "./MLDetectionHUD";
import {
  calculateDistance,
  calculateBearing,
  smoothAngle,
  snapToRoute,
} from "./utils/navigationMath";

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

const DEFAULT_CENTER = [12.9716, 77.5946]; // Bengaluru
const getApiBaseUrl = () => {
  const host = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
  const apiHost = host === "localhost" ? "127.0.0.1" : host;
  return `http://${apiHost}:8001`;
};
const ROUTE_COLORS = ["#2563eb"];

const formatDistanceStr = (meters) => {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
};

const formatDurationStr = (seconds) => {
  const mins = Math.round(seconds / 60);
  const hrs = Math.floor(mins / 60);
  const rem = mins % 60;
  if (hrs > 0) return `${hrs} hr ${rem} min`;
  return `${rem} min`;
};

const parseSpeedLimit = (value) => {
  const match = String(value || "").match(
    /(?:Speed limit\s*\()?\s*(\d+(?:\.\d+)?)\s*(km\/h|kmh|mph)?/i
  );
  if (!match) return null;
  const speed = Number(match[1]);
  return match[2]?.toLowerCase() === "mph" ? speed * 1.60934 : speed;
};

// Map controller to adjust view
function MapController({ center, zoom, routeBounds, followLocation, headingUp, currentHeading }) {
  const map = useMap();

  useEffect(() => {
    if (followLocation) {
      map.setView([followLocation.lat, followLocation.lon], Math.max(map.getZoom(), 16), {
        animate: true,
      });
    } else if (routeBounds) {
      map.fitBounds(routeBounds, { padding: [60, 60], maxZoom: 15 });
    } else if (center) {
      map.setView(center, zoom || 13);
    }
  }, [center, zoom, routeBounds, followLocation, map]);

  return null;
}

// Bounding-box filtered road network layer
function RoadNetworkLayer({ onStatus, currentLocation, onRoadContext }) {
  const map = useMap();
  const [features, setFeatures] = useState([]);
  const requestTimer = useRef(null);
  const requestController = useRef(null);

  // Karnataka bounds for road network restriction
  const KARNATAKA_BOUNDS = {
    minLat: 11.5, maxLat: 18.5,
    minLon: 74.0, maxLon: 78.6,
  };

  const loadRoads = useCallback(() => {
    clearTimeout(requestTimer.current);
    requestTimer.current = setTimeout(async () => {
      const center = map.getCenter();

      // KARNATAKA RESTRICTION: Only load roads within Karnataka
      if (
        center.lat < KARNATAKA_BOUNDS.minLat || center.lat > KARNATAKA_BOUNDS.maxLat ||
        center.lng < KARNATAKA_BOUNDS.minLon || center.lng > KARNATAKA_BOUNDS.maxLon
      ) {
        requestController.current?.abort();
        setFeatures([]);
        onStatus("Road data: Karnataka only");
        return;
      }

      if (map.getZoom() < 8) {
        setFeatures([]);
        onStatus("Zoom in to view Karnataka roads");
        return;
      }

      requestController.current?.abort();
      const controller = new AbortController();
      requestController.current = controller;
      const bounds = map.getBounds();
      const halfLat = Math.min((bounds.getNorth() - bounds.getSouth()) / 2, 0.5);
      const halfLon = Math.min((bounds.getEast() - bounds.getWest()) / 2, 0.5);
      const params = new URLSearchParams({
        min_lat: String(Math.max(KARNATAKA_BOUNDS.minLat, center.lat - halfLat)),
        max_lat: String(Math.min(KARNATAKA_BOUNDS.maxLat, center.lat + halfLat)),
        min_lon: String(Math.max(KARNATAKA_BOUNDS.minLon, center.lng - halfLon)),
        max_lon: String(Math.min(KARNATAKA_BOUNDS.maxLon, center.lng + halfLon)),
        max_features: "800",
      });

      onStatus("Loading Karnataka roads");
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/roads?${params}`, {
          signal: controller.signal,
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Road network unavailable");
        }
        setFeatures(data.features || []);
        onStatus(`Karnataka roads: ${data.count}${data.truncated ? "+" : ""}`);
      } catch (error) {
        if (error.name !== "AbortError") {
          setFeatures([]);
          onStatus("OSM roads unavailable");
        }
      }
    }, 400);
  }, [map, onStatus]);

  useMapEvents({ moveend: loadRoads, zoomend: loadRoads });

  useEffect(() => {
    loadRoads();
    return () => {
      clearTimeout(requestTimer.current);
      requestController.current?.abort();
    };
  }, [loadRoads]);

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
          color: properties.highway === "motorway" ? "#d97706" : "#475569",
          weight: properties.highway === "motorway" ? 3 : 1.5,
          opacity: 0.5,
        }}
      >
        <Popup>
          <strong>{properties.name || "Unnamed road"}</strong>
          <br />
          {properties.highway || "Road"} · {properties.source} network
        </Popup>
      </Polyline>
    );
  });
}

export default function RoutePlanner() {
  const mapRef = useRef(null);
  const lastTripLocationRef = useRef(null);
  const lastSpokenWarningRef = useRef({ signature: "", timestamp: 0 });
  const offRouteCounterRef = useRef(0);

  // Search input state
  const [start, setStart] = useState("");
  const [destination, setDestination] = useState("");
  const [startCoords, setStartCoords] = useState(null);
  const [destinationCoords, setDestinationCoords] = useState(null);

  // Routing state
  const [routes, setRoutes] = useState([]);
  const [selectedRoute, setSelectedRoute] = useState(0);
  const [routeBounds, setRouteBounds] = useState(null);

  // Map & Controls state
  const [mapCenter, setMapCenter] = useState(DEFAULT_CENTER);
  const [mapZoom, setMapZoom] = useState(12);
  const [mapStyle, setMapStyle] = useState("standard");
  const [showRoadNetwork, setShowRoadNetwork] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);
  const [showTraffic, setShowTraffic] = useState(true);
  const [headingUp, setHeadingUp] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true);

  // Context & Metrics state
  const [activeLocationName, setActiveLocationName] = useState("Bengaluru, Karnataka");
  const [trafficContext, setTrafficContext] = useState(null);
  const [weatherContext, setWeatherContext] = useState(null);
  const [roadContext, setRoadContext] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [roadNetworkStatus, setRoadNetworkStatus] = useState("Loading Bengaluru roads");

  // UI state
  const [loading, setLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [error, setError] = useState("");
  const [karnatakaError, setKarnatakaError] = useState(null);
  const [recentDetections, setRecentDetections] = useState([]);

  // Trip State
  const [tripStatus, setTripStatus] = useState("inactive"); // inactive, in_progress, completed
  const [tripData, setTripData] = useState({
    startTime: null,
    endTime: null,
    distanceTraveled: 0,
    currentSpeedKmh: 0,
    roadDamageDetections: [],
    trafficSignsDetected: [],
    currentLocation: null,
    currentHeading: 0,
  });

  // Navigation Cursor Icons
  const navigationMarkerIcon = (heading = 0) =>
    L.divIcon({
      className: "nav-cursor-wrapper",
      html: `<div class="nav-cursor-arrow" style="transform: rotate(${heading}deg);">▲</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });

  // IMPROVEMENT: Dynamic hotspot icons based on risk level
  const getHotspotIcon = (riskLevel = "High") => {
    const riskColors = {
      "High": "#dc2626",
      "Medium": "#f59e0b",
      "Low": "#16a34a",
    };
    const color = riskColors[riskLevel] || riskColors["High"];
    return L.divIcon({
      className: "hotspot-marker",
      html: `<div class="hotspot-dot" style="background-color: ${color}; box-shadow: 0 0 10px ${color};"></div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });
  };

  const startMarkerIcon = L.divIcon({
    className: "start-point-marker",
    html: '<div class="start-dot-icon">A</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

  const destMarkerIcon = L.divIcon({
    className: "dest-point-marker",
    html: '<div class="dest-dot-icon">B</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

  const handleTrafficUpdate = useCallback((traffic, locationKey) => {
    setTrafficContext(traffic ? { data: traffic, locationKey } : null);
  }, []);

  const handleWeatherUpdate = useCallback((weather, locationKey) => {
    setWeatherContext(weather ? { data: weather, locationKey } : null);
  }, []);

  // Fetch hotspots
  useEffect(() => {
    const fetchHotspots = async () => {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/hotspots`);
        if (response.ok) {
          const data = await response.json();
          setHotspots(data || []);
        }
      } catch (err) {
        console.error("Hotspots load error:", err);
      }
    };
    fetchHotspots();
  }, []);

  // Karnataka geographic bounds (mirrors backend restriction)
  const KARNATAKA_BOUNDS = {
    minLat: 11.5, maxLat: 18.5,
    minLon: 74.0, maxLon: 78.6,
  };

  const isInKarnataka = (lat, lon) =>
    lat >= KARNATAKA_BOUNDS.minLat && lat <= KARNATAKA_BOUNDS.maxLat &&
    lon >= KARNATAKA_BOUNDS.minLon && lon <= KARNATAKA_BOUNDS.maxLon;

  // KARNATAKA RESTRICTION: Validate location is within Karnataka
  const validateKarnatakaLocation = (lat, lon, locationName = "Location") => {
    if (!isInKarnataka(lat, lon)) {
      const message = `${locationName} is outside Karnataka. Please select a location within Karnataka, India.`;
      setKarnatakaError({ message, locationName });
      setTimeout(() => setKarnatakaError(null), 5000);
      return {
        valid: false,
        message
      };
    }
    return { valid: true, message: "" };
  };

  // Geocode location helper — Karnataka only
  const geocodeLocation = async (place) => {
    const query = place.trim();
    if (!query) throw new Error("Please enter a location.");

    // Handle manual lat,lon input
    const match = query.match(/^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/);
    if (match) {
      const lat = Number(match[1]);
      const lon = Number(match[2]);
      if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
        // KARNATAKA RESTRICTION: Validate coordinates
        const validation = validateKarnatakaLocation(lat, lon, "Coordinates");
        if (!validation.valid) {
          throw new Error(validation.message);
        }
        return { lat, lon, display_name: query };
      }
      throw new Error("Invalid coordinates.");
    }

    const res = await fetch(`${getApiBaseUrl()}/api/geocode?query=${encodeURIComponent(query)}`);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      // IMPROVEMENT: Better error messages based on status code
      if (res.status === 429) {
        throw new Error("Location search is busy. Please wait a moment and try again.");
      } else if (res.status === 504) {
        throw new Error("Location search timed out. Please try again.");
      } else if (res.status === 503) {
        throw new Error("Location search service is temporarily unavailable. Please try again later.");
      } else if (res.status === 404) {
        throw new Error(`"${query}" was not found in Karnataka. Please search for a Karnataka location.`);
      } else {
        throw new Error(errData.detail || "Location search service unavailable.");
      }
    }
    const data = await res.json();
    if (!data.locations?.length) throw new Error(`Location not found in Karnataka: ${query}`);
    return data.locations[0];
  };

  // Get current GPS location
  const useCurrentLocation = () => {
    setError("");
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }

    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        const coords = { lat: latitude, lon: longitude };

        // KARNATAKA RESTRICTION: Validate GPS coordinates
        const validation = validateKarnatakaLocation(latitude, longitude, "Current location");
        if (!validation.valid) {
          setError(validation.message);
          setLocationLoading(false);
          return;
        }

        setStartCoords(coords);
        setStart(`${latitude.toFixed(6)}, ${longitude.toFixed(6)}`);
        setActiveLocationName("Current Location");
        setMapCenter([latitude, longitude]);
        setMapZoom(16);
        setRouteBounds(null);
        setLocationLoading(false);
      },
      (err) => {
        setError("Unable to retrieve GPS location. Please verify browser permissions.");
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 12000 }
    );
  };

  // Calculate routes
  const findRoutes = async (startLocObj, destLocObj) => {
    setError("");
    setLoading(true);

    try {
      const startLoc = startLocObj || (startCoords ? startCoords : await geocodeLocation(start));
      const destLoc = destLocObj || (destinationCoords ? destinationCoords : await geocodeLocation(destination));

      // KARNATAKA RESTRICTION: Validate both start and destination
      const startValidation = validateKarnatakaLocation(startLoc.lat, startLoc.lon, "Start location");
      if (!startValidation.valid) {
        throw new Error(startValidation.message);
      }

      const destValidation = validateKarnatakaLocation(destLoc.lat, destLoc.lon, "Destination");
      if (!destValidation.valid) {
        throw new Error(destValidation.message);
      }

      setStartCoords(startLoc);
      setDestinationCoords(destLoc);
      setActiveLocationName(destLoc.display_name?.split(",")[0] || "Destination");

      // Query route API
      const proxyUrl = `${getApiBaseUrl()}/api/routes?start_lon=${startLoc.lon}&start_lat=${startLoc.lat}&dest_lon=${destLoc.lon}&dest_lat=${destLoc.lat}&alternatives=true`;
      let res = await fetch(proxyUrl).catch(() => null);

      if (!res || !res.ok) {
        // KARNATAKA RESTRICTION: Do not use OSRM fallback for Karnataka restriction
        const errData = await res?.json().catch(() => ({}));
        throw new Error(errData.detail || "Could not compute route. Both locations must be within Karnataka.");
      }

      const data = await res.json();

      if (data.code !== "Ok" || !data.routes?.length) {
        throw new Error("No driving route found between these locations.");
      }

      const formattedRoutes = data.routes.map((rt, idx) => ({
        id: idx,
        distance: rt.distance,
        duration: rt.duration,
        geometry: rt.geometry.coordinates.map(([lon, lat]) => [lat, lon]),
        color: ROUTE_COLORS[idx % ROUTE_COLORS.length],
        steps: rt.legs?.flatMap((leg) => leg.steps || []) || [],
      }));

      setRoutes(formattedRoutes);
      setSelectedRoute(0);
      setRouteBounds(L.latLngBounds(formattedRoutes[0].geometry));
    } catch (err) {
      setError(err.message || "Route calculation failed.");
    } finally {
      setLoading(false);
    }
  };

  // Recalculate route automatically when off-route
  const recalculateOffRoute = useCallback(async (currentLoc) => {
    if (!destinationCoords || !currentLoc) return;
    try {
      const startLoc = { lat: currentLoc.lat, lon: currentLoc.lon };
      setStartCoords(startLoc);
      setStart(`${currentLoc.lat.toFixed(6)}, ${currentLoc.lon.toFixed(6)}`);

      const proxyUrl = `${getApiBaseUrl()}/api/routes?start_lon=${startLoc.lon}&start_lat=${startLoc.lat}&dest_lon=${destinationCoords.lon}&dest_lat=${destinationCoords.lat}&alternatives=false`;
      const res = await fetch(proxyUrl);
      if (!res.ok) return;
      const data = await res.json();
      if (data.code === "Ok" && data.routes?.length) {
        const rt = data.routes[0];
        const newRoute = {
          id: 0,
          distance: rt.distance,
          duration: rt.duration,
          geometry: rt.geometry.coordinates.map(([lon, lat]) => [lat, lon]),
          color: ROUTE_COLORS[0],
          steps: rt.legs?.flatMap((leg) => leg.steps || []) || [],
        };
        setRoutes([newRoute]);
        setSelectedRoute(0);
        offRouteCounterRef.current = 0;
      }
    } catch (e) {
      console.warn("Off-route recalculation failed", e);
    }
  }, [destinationCoords]);

  // Start Trip
  const startTrip = () => {
    if (!routes[selectedRoute]) {
      setError("Please select a route first.");
      return;
    }
    setTripStatus("in_progress");
    setTripData({
      startTime: new Date(),
      endTime: null,
      distanceTraveled: 0,
      currentSpeedKmh: 0,
      roadDamageDetections: [],
      trafficSignsDetected: [],
      currentLocation: startCoords,
      currentHeading: 0,
    });
    lastTripLocationRef.current = null;
    offRouteCounterRef.current = 0;
    setError("");
  };

  // End Trip
  const endTrip = () => {
    setTripStatus("completed");
    setTripData((prev) => ({
      ...prev,
      endTime: new Date(),
    }));
  };

  const clearAll = () => {
    setStart("");
    setDestination("");
    setStartCoords(null);
    setDestinationCoords(null);
    setRoutes([]);
    setSelectedRoute(0);
    setRouteBounds(null);
    setMapCenter(DEFAULT_CENTER);
    setMapZoom(12);
    setError("");
    setTripStatus("inactive");
    // Reset trip data completely
    setTripData({
      startTime: null,
      endTime: null,
      distanceTraveled: 0,
      currentSpeedKmh: 0,
      roadDamageDetections: [],
      trafficSignsDetected: [],
      currentLocation: null,
      currentHeading: 0,
    });
    setRecentDetections([]);
    setKarnatakaError(null);
  };

  // Handlers for ML camera detections
  const handleRoadDamageDetection = (detection) => {
    if (tripStatus === "in_progress") {
      const item = {
        ...detection,
        id: Date.now() + Math.random(),
        type: "road_damage",
        timestamp: new Date(),
        className: detection.class_name || detection.className || "Road Damage",
      };
      setRecentDetections((prev) => [item, ...prev].slice(0, 4));
      setTripData((prev) => ({
        ...prev,
        roadDamageDetections: [...prev.roadDamageDetections, item],
      }));
    }
  };

  const handleTrafficSignDetection = (sign) => {
    if (tripStatus === "in_progress") {
      const item = {
        ...sign,
        id: Date.now() + Math.random(),
        type: "traffic_sign",
        timestamp: new Date(),
        className: sign.sign_name || sign.className || "Traffic Sign",
      };
      setRecentDetections((prev) => [item, ...prev].slice(0, 4));
      setTripData((prev) => ({
        ...prev,
        trafficSignsDetected: [...prev.trafficSignsDetected, item],
      }));
    }
  };

  // Continuous GPS Tracking during active navigation trip
  useEffect(() => {
    let watchId = null;
    if (tripStatus === "in_progress" && navigator.geolocation) {
      watchId = navigator.geolocation.watchPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          const rawCoords = { lat: latitude, lon: longitude };
          const activeRt = routes[selectedRoute];

          // Snap GPS to route and smooth heading
          let displayLat = latitude;
          let displayLon = longitude;
          let targetHeading = pos.coords.heading || 0;

          if (activeRt?.geometry?.length) {
            const snapped = snapToRoute(latitude, longitude, activeRt.geometry);
            if (!snapped.isOffRoute) {
              displayLat = snapped.snappedLat;
              displayLon = snapped.snappedLon;
              targetHeading = snapped.segmentBearing || targetHeading;
              offRouteCounterRef.current = 0;
            } else {
              offRouteCounterRef.current += 1;
              if (offRouteCounterRef.current >= 3) {
                recalculateOffRoute(rawCoords);
              }
            }
          }

          const prevLoc = lastTripLocationRef.current;
          if (prevLoc && (!targetHeading || isNaN(targetHeading))) {
            targetHeading = calculateBearing(prevLoc.lat, prevLoc.lon, latitude, longitude);
          }

          // Smooth heading calculation using 0/360 wrap-around logic
          const newHeading = prevLoc
            ? smoothAngle(prevLoc.heading || 0, targetHeading || 0, 0.25)
            : targetHeading || 0;

          const speedKmh = pos.coords.speed != null ? pos.coords.speed * 3.6 : 0;
          const distDelta = prevLoc ? calculateDistance(prevLoc.lat, prevLoc.lon, displayLat, displayLon) : 0;

          const newLoc = {
            lat: displayLat,
            lon: displayLon,
            heading: newHeading,
            timestamp: pos.timestamp,
          };
          lastTripLocationRef.current = newLoc;

          setTripData((prev) => ({
            ...prev,
            currentLocation: newLoc,
            currentSpeedKmh: speedKmh,
            currentHeading: newHeading,
            distanceTraveled: prev.distanceTraveled + distDelta,
          }));
        },
        (err) => {
          console.warn("GPS tracking warning", err);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 3000 }
      );
    }

    return () => {
      if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    };
  }, [tripStatus, routes, selectedRoute, recalculateOffRoute]);

  // Derive turn-by-turn instruction steps
  const activeRouteData = routes[selectedRoute];
  const activeSteps = activeRouteData?.steps || [];
  let currentStep = null;
  let nextStep = null;
  let distanceToManeuver = 0;

  if (activeSteps.length && tripData.currentLocation) {
    let nearestIdx = 0;
    let minDist = Infinity;
    activeSteps.forEach((st, idx) => {
      if (st.maneuver?.location) {
        const [stLon, stLat] = st.maneuver.location;
        const d = calculateDistance(tripData.currentLocation.lat, tripData.currentLocation.lon, stLat, stLon);
        if (d < minDist) {
          minDist = d;
          nearestIdx = idx;
        }
      }
    });

    currentStep = activeSteps[nearestIdx] || activeSteps[0];
    nextStep = activeSteps[nearestIdx + 1] || null;
    distanceToManeuver = minDist < 10000 ? minDist : currentStep?.distance || 0;
  }

  const contextLocation = tripData.currentLocation || startCoords || { lat: 12.9716, lon: 77.5946 };
  const locationKey = `${contextLocation.lat.toFixed(2)},${contextLocation.lon.toFixed(2)}`;

  return (
    <div className="fullscreen-nav-app">
      {/* Karnataka Restriction Error Banner */}
      {karnatakaError && (
        <div className="karnataka-error-banner">
          <span className="error-icon">🚫</span>
          <h3>Outside Service Area</h3>
          <p>{karnatakaError.message}</p>
        </div>
      )}

      {/* Search & Destination Top Card */}
      <SearchPanel
        startQuery={start}
        setStartQuery={setStart}
        destQuery={destination}
        setDestQuery={setDestination}
        onSelectStart={(loc) => loc && setStartCoords({ lat: loc.lat, lon: loc.lon })}
        onSelectDest={(loc) => {
          if (loc) {
            const d = { lat: loc.lat, lon: loc.lon };
            setDestinationCoords(d);
            findRoutes(startCoords, d);
          }
        }}
        onUseCurrentLocation={useCurrentLocation}
        onGetDirections={() => findRoutes()}
        onClearAll={clearAll}
        loading={loading}
        locationLoading={locationLoading}
        hasRoutes={routes.length > 0}
        tripStatus={tripStatus}
      />

      {/* Turn-By-Turn Banner (Active Navigation) */}
      {tripStatus === "in_progress" && currentStep && (
        <TurnByTurnBanner
          currentStep={currentStep}
          nextStep={nextStep}
          distanceToManeuver={distanceToManeuver}
          audioEnabled={audioEnabled}
        />
      )}

      {/* Floating Right Map Controls */}
      <NavigationControls
        onRecenter={() => {
          if (tripData.currentLocation && mapRef.current) {
            mapRef.current.setView([tripData.currentLocation.lat, tripData.currentLocation.lon], 16, { animate: true });
          } else if (startCoords && mapRef.current) {
            mapRef.current.setView([startCoords.lat, startCoords.lon], 15, { animate: true });
          }
        }}
        headingUp={headingUp}
        onToggleHeadingMode={() => setHeadingUp((prev) => !prev)}
        showTraffic={showTraffic}
        onToggleTraffic={() => setShowTraffic((prev) => !prev)}
        showHotspots={showHotspots}
        onToggleHotspots={() => setShowHotspots((prev) => !prev)}
        showRoadNetwork={showRoadNetwork}
        onToggleRoadNetwork={() => setShowRoadNetwork((prev) => !prev)}
        audioEnabled={audioEnabled}
        onToggleAudio={() => setAudioEnabled((prev) => !prev)}
        compassHeading={tripData.currentHeading}
      />

      {/* Live ML Detections Notification HUD */}
      {tripStatus === "in_progress" && (
        <MLDetectionHUD recentDetections={recentDetections} />
      )}

      {/* Weather & Traffic Floating Card (Non-Obtrusive) */}
      <div className="env-widgets-container">
        {showTraffic && (
          <TrafficCard
            location={contextLocation}
            locationName={activeLocationName}
            onTrafficUpdate={handleTrafficUpdate}
          />
        )}
        <WeatherCard
          location={contextLocation}
          locationName={activeLocationName}
          onWeatherUpdate={handleWeatherUpdate}
        />
        {/* Speed Recommendation - Only show during active trip */}
        {tripStatus === "in_progress" && (
          <SpeedRecommendation
            roadDamageDetections={tripData.roadDamageDetections}
            trafficSignDetections={tripData.trafficSignsDetected}
            trafficData={trafficContext}
            weatherData={weatherContext}
            currentSpeed={tripData.currentSpeedKmh}
          />
        )}
      </div>

      {/* Main Fullscreen Map */}
      <main className="fullscreen-map-wrapper">
        <MapContainer
          center={DEFAULT_CENTER}
          zoom={12}
          className="fullscreen-leaflet-map"
          whenReady={(e) => {
            mapRef.current = e.target;
          }}
        >
          <MapController
            center={mapCenter}
            zoom={mapZoom}
            routeBounds={routeBounds}
            followLocation={tripStatus === "in_progress" ? tripData.currentLocation : null}
            headingUp={headingUp}
            currentHeading={tripData.currentHeading}
          />

          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url={
              mapStyle === "satellite"
                ? "https://server.arcgison.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                : "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            }
          />

          {/* Start Marker */}
          {startCoords && (
            <Marker position={[startCoords.lat, startCoords.lon]} icon={startMarkerIcon}>
              <Popup>Starting Location</Popup>
            </Marker>
          )}

          {/* Destination Marker */}
          {destinationCoords && (
            <Marker position={[destinationCoords.lat, destinationCoords.lon]} icon={destMarkerIcon}>
              <Popup>Destination: {activeLocationName}</Popup>
            </Marker>
          )}

          {/* Smooth Dynamic Vehicle Pointer Cursor */}
          {tripStatus === "in_progress" && tripData.currentLocation && (
            <Marker
              position={[tripData.currentLocation.lat, tripData.currentLocation.lon]}
              icon={navigationMarkerIcon(tripData.currentHeading)}
            >
              <Popup>Current Navigation Cursor</Popup>
            </Marker>
          )}

          {/* Route Alternatives */}
          {routes.map((rt, idx) => (
            <Polyline
              key={rt.id}
              positions={rt.geometry}
              pathOptions={{
                color: rt.color,
                weight: selectedRoute === idx ? 7 : 4,
                opacity: selectedRoute === idx ? 0.95 : 0.45,
                dashArray: selectedRoute === idx ? null : "8, 8",
              }}
              eventHandlers={{
                click: () => {
                  setSelectedRoute(idx);
                  setRouteBounds(L.latLngBounds(rt.geometry));
                },
              }}
            />
          ))}

          {/* Bengaluru Road Overlay */}
          {showRoadNetwork && (
            <RoadNetworkLayer
              onStatus={setRoadNetworkStatus}
              currentLocation={tripData.currentLocation}
              onRoadContext={(r) => setRoadContext(r)}
            />
          )}

          {/* Historical Accident Hotspots Layer */}
          {showHotspots &&
            hotspots.map((hotspot, idx) => {
              if (hotspot.latitude && hotspot.longitude) {
                const riskLevel = hotspot.Accident_Rate_Category || hotspot.accident_rate_category || "High";
                return (
                  <Marker
                    key={`hs-${idx}`}
                    position={[hotspot.latitude, hotspot.longitude]}
                    icon={getHotspotIcon(riskLevel)}
                  >
                    <Popup>
                      <div className="hotspot-popup">
                        <strong>Historical Accident Hotspot</strong>
                        <p>
                          <strong>Zone:</strong> {hotspot.Zone || hotspot.zone || "Bengaluru"}
                        </p>
                        <p>
                          <strong>Police Station:</strong> {hotspot.Station || hotspot.station || "N/A"}
                        </p>
                        <p>
                          <strong>Total Accidents:</strong> {hotspot.Total_Accidents || hotspot.total_accidents || "N/A"}
                        </p>
                        <p>
                          <strong>Risk Level:</strong> {riskLevel}
                        </p>
                        <small className="hotspot-disclaimer">
                          Historical station-level data. Not crash-point probability.
                        </small>
                      </div>
                    </Popup>
                  </Marker>
                );
              }
              return null;
            })}
        </MapContainer>
      </main>

      {/* Bottom Floating Navigation Stats Bar - Hidden when trip is completed */}
      {tripStatus !== "completed" && (
        <NavigationStatsBar
          tripStatus={tripStatus}
          onStartTrip={startTrip}
          onEndTrip={endTrip}
          activeRoute={activeRouteData}
          currentSpeed={tripData.currentSpeedKmh}
          currentRoadName={roadContext?.name || currentStep?.name || "Bengaluru Road"}
          destinationName={activeLocationName}
          hasRoutes={routes.length > 0}
          selectedRouteIndex={selectedRoute}
          onSelectRouteIndex={(idx) => {
            setSelectedRoute(idx);
            setRouteBounds(L.latLngBounds(routes[idx].geometry));
          }}
          routesList={routes}
        />
      )}

      {/* Hidden Camera Microservice Worker */}
      <div style={{ display: "none" }}>
        <CameraCapture
          tripStatus={tripStatus}
          onRoadDamageDetection={handleRoadDamageDetection}
          onTrafficSignDetection={handleTrafficSignDetection}
        />
      </div>

      {/* Post-Trip Summary Modal */}
      {tripStatus === "completed" && (
        <div className="trip-summary-overlay">
          <TripSummary
            tripData={tripData}
            startLocation={start}
            destination={destination}
            routeDistance={activeRouteData?.distance}
            onStartNewTrip={clearAll}
          />
        </div>
      )}
    </div>
  );
}