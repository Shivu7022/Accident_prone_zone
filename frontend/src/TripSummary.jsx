import "./TripSummary.css";

export default function TripSummary({ tripData, startLocation, destination, routeDistance, onStartNewTrip }) {
  const duration =
    tripData.startTime && tripData.endTime
      ? Math.floor(
          (new Date(tripData.endTime) - new Date(tripData.startTime)) / 1000
        )
      : 0;

  const formatDistance = (meters) => {
    if (meters >= 1000) {
      return `${(meters / 1000).toFixed(1)} km`;
    }
    return `${Math.round(meters)} m`;
  };

  const formatDuration = (seconds) => {
    const totalMinutes = Math.round(seconds / 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;

    if (hours > 0) {
      return `${hours} hr ${minutes} min`;
    }
    return `${minutes} min`;
  };

  return (
    <div className="trip-summary">
      <div className="trip-summary-header">
        <div className="trip-summary-icon">🏁</div>
        <div>
          <h2>Trip Completed</h2>
          <p>Your journey has been recorded</p>
        </div>
      </div>

      <div className="trip-summary-route">
        <div className="trip-route-point">
          <span className="route-point-icon">🟢</span>
          <div>
            <small>From</small>
            <strong>{startLocation || "Starting Point"}</strong>
          </div>
        </div>

        <div className="trip-route-line" />

        <div className="trip-route-point">
          <span className="route-point-icon">🔴</span>
          <div>
            <small>To</small>
            <strong>{destination || "Destination"}</strong>
          </div>
        </div>
      </div>

      <div className="trip-summary-stats">
        <div className="summary-stat">
          <span>📏 Distance</span>
          <strong>{formatDistance(tripData.distanceTraveled || routeDistance || 0)}</strong>
        </div>

        <div className="summary-stat">
          <span>⏱️ Duration</span>
          <strong>{formatDuration(duration)}</strong>
        </div>

        <div className="summary-stat">
          <span>🚧 Damage Detected</span>
          <strong>{tripData.roadDamageDetections?.length || 0}</strong>
        </div>

        <div className="summary-stat">
          <span>🚦 Confirmed Sign Regions</span>
          <strong>{tripData.trafficSignsDetected?.length || 0}</strong>
        </div>
      </div>

      {tripData.roadDamageDetections?.length > 0 && (
        <div className="trip-summary-detections">
          <h3>Road Damage Detected</h3>
          <div className="detection-list">
            {tripData.roadDamageDetections.map((detection, index) => (
              <div key={index} className="detection-item">
                <strong>{detection.class_name || detection.class || "Road Damage"}</strong>
                <span>
                  {typeof detection.confidence === "number"
                    ? `${detection.confidence.toFixed(1)}%`
                    : detection.confidence || "N/A"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tripData.trafficSignsDetected?.length > 0 && (
        <div className="trip-summary-signs">
          <h3>Confirmed Sign Regions</h3>
          <div className="sign-list">
            {tripData.trafficSignsDetected.map((sign, index) => (
              <div key={index} className="sign-item">
                <strong>{sign.sign_name || "Unknown Sign"}</strong>
                <span>
                  {typeof sign.confidence === "number"
                    ? `${sign.confidence.toFixed(1)}%`
                    : sign.confidence || "N/A"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        type="button"
        className="start-new-trip-button"
        onClick={onStartNewTrip}
      >
        🚀 Start New Trip
      </button>
    </div>
  );
}
