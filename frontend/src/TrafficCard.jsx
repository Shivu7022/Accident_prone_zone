import { useCallback, useEffect, useState } from "react";
import "./TrafficCard.css";

const API_URL = "http://127.0.0.1:8001/api/traffic";

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
  });
  const traffic = trafficResult.locationKey === locationKey
    ? trafficResult.traffic
    : null;
  const error = trafficResult.locationKey === locationKey
    ? trafficResult.error
    : "";

  const fetchTraffic = useCallback(async () => {
    if (!hasLocation) return;

    try {
      const response = await fetch(
        `${API_URL}?lat=${latitude}&lon=${longitude}`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch traffic data");
      }

      const data = await response.json();
      setTrafficResult({ locationKey, traffic: data, error: "" });
      onTrafficUpdate?.(data, locationKey);
    } catch (err) {
      setTrafficResult((previous) => ({
        locationKey,
        traffic: previous.locationKey === locationKey
          ? previous.traffic
          : null,
        error: err.message,
      }));
    }
  }, [hasLocation, latitude, longitude, locationKey, onTrafficUpdate]);

  useEffect(() => {
    if (!hasLocation) return;

    fetchTraffic();

    const interval = setInterval(fetchTraffic, 60000);

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
      <h2>🚦 Live Traffic{locationName ? ` - ${locationName}` : ""}</h2>

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

      <button onClick={fetchTraffic}>Refresh Traffic</button>
    </div>
  );
}