import { useCallback, useEffect, useState } from "react";
import "./TrafficCard.css";

const getApiUrl = () => {
  const host = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
  const apiHost = host === "localhost" ? "127.0.0.1" : host;
  return `http://${apiHost}:8001/api/traffic`;
};

export default function TrafficCard({ location, locationName, onTrafficUpdate }) {
  const hasLocation =
    Number.isFinite(location?.lat) && Number.isFinite(location?.lon);
  const latitude = hasLocation ? Number(Number(location.lat).toFixed(2)) : null;
  const longitude = hasLocation ? Number(Number(location.lon).toFixed(2)) : null;
  const locationKey = hasLocation ? `${latitude},${longitude}` : null;
  const [trafficResult, setTrafficResult] = useState({
    locationKey: null,
    traffic: null,
    error: "",
    lastUpdated: null,
  });
  const traffic = trafficResult.locationKey === locationKey
    ? trafficResult.traffic
    : null;
  const error = trafficResult.locationKey === locationKey
    ? trafficResult.error
    : "";
  const lastUpdated = trafficResult.locationKey === locationKey
    ? trafficResult.lastUpdated
    : null;

  const fetchTraffic = useCallback(async () => {
    if (!hasLocation) return;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 25000);

      const response = await fetch(
        `${getApiUrl()}?lat=${latitude}&lon=${longitude}`,
        { signal: controller.signal }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        // IMPROVEMENT: Better error messages based on status code
        if (response.status === 500) {
          throw new Error("Traffic service is temporarily unavailable");
        } else if (response.status === 503) {
          throw new Error("Traffic service is currently down");
        } else {
          throw new Error("Failed to fetch traffic data");
        }
      }

      const data = await response.json();
      setTrafficResult({ locationKey, traffic: data, error: "", lastUpdated: new Date() });
      onTrafficUpdate?.(data, locationKey);
    } catch (err) {
      if (err.name === 'AbortError') {
        setTrafficResult((previous) => ({
          locationKey,
          traffic: previous.locationKey === locationKey
            ? previous.traffic
            : null,
          error: "Request timed out - please try again",
          lastUpdated: previous.locationKey === locationKey ? previous.lastUpdated : null,
        }));
      } else {
        setTrafficResult((previous) => ({
          locationKey,
          traffic: previous.locationKey === locationKey
            ? previous.traffic
            : null,
          error: err.message || "Unable to load traffic data",
          lastUpdated: previous.locationKey === locationKey ? previous.lastUpdated : null,
        }));
      }
    }
  }, [hasLocation, latitude, longitude, locationKey, onTrafficUpdate]);

  useEffect(() => {
    if (!hasLocation) return;

    fetchTraffic();

    // IMPROVEMENT: Reduce interval to 30 seconds for more frequent updates
    const interval = setInterval(fetchTraffic, 30000);

    return () => clearInterval(interval);
  }, [fetchTraffic, hasLocation, onTrafficUpdate]);

  const getCongestion = () => {
    if (
      !traffic ||
      !traffic.free_flow_speed_kmh ||
      traffic.current_speed_kmh == null
    ) {
      return { level: "Unavailable", color: "#6b7280", percentage: null };
    }

    const percentage =
      ((traffic.free_flow_speed_kmh - traffic.current_speed_kmh) /
        traffic.free_flow_speed_kmh) *
      100;

    if (percentage < 20) {
      return { level: "Low", color: "#16a34a", percentage };
    }

    if (percentage < 50) {
      return { level: "Moderate", color: "#f59e0b", percentage };
    }

    return { level: "High", color: "#dc2626", percentage };
  };

  const congestion = getCongestion();

  if (!hasLocation) {
    return (
      <div className="traffic-card">
        <h2>Live Traffic</h2>
        <p>Choose a starting point or share your location to load traffic.</p>
      </div>
    );
  }

  return (
    <div className="traffic-card">
      <div className="traffic-header">
        <h2>🚦 Live Traffic{locationName ? ` - ${locationName}` : ""}</h2>
        {/* IMPROVEMENT: Add live indicator pulsing dot */}
        {traffic && !error && (
          <div className="live-indicator">
            <span className="live-dot"></span>
            <span className="live-text">LIVE</span>
          </div>
        )}
      </div>

      {error && <p className="traffic-error">{error}</p>}

      {!traffic && !error && <p>Loading traffic data...</p>}

      {traffic && (
        <>
          <div
            className="congestion-status"
            style={{ backgroundColor: congestion.color }}
          >
            {congestion.level} Congestion
          </div>

          <p>
            <strong>Current Speed:</strong>{" "}
            {traffic.current_speed_kmh ?? "N/A"} km/h
          </p>

          <p>
            <strong>Free-Flow Speed:</strong>{" "}
            {traffic.free_flow_speed_kmh ?? "N/A"} km/h
          </p>

          <p>
            <strong>Travel Time:</strong>{" "}
            {traffic.current_travel_time_seconds ?? "N/A"} seconds
          </p>

          <p>
            <strong>Speed Reduction:</strong>{" "}
            {congestion.percentage == null
              ? "N/A"
              : `${Math.max(0, congestion.percentage).toFixed(1)}%`}
          </p>

          <p>
            <strong>Confidence:</strong>{" "}
            {traffic.confidence ?? "N/A"}
          </p>
        </>
      )}

      {/* IMPROVEMENT: Show last updated timestamp with age */}
      {lastUpdated && (
        <p className="traffic-timestamp">
          Last updated: {lastUpdated.toLocaleTimeString()}
          <span className="timestamp-age">
            ({Math.round((Date.now() - lastUpdated) / 1000)}s ago)
          </span>
        </p>
      )}

      <button onClick={fetchTraffic}>Refresh Traffic</button>
    </div>
  );
}