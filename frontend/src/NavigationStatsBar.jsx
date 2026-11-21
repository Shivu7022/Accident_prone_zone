import React from "react";
import "./NavigationStatsBar.css";

export default function NavigationStatsBar({
  tripStatus,
  onStartTrip,
  onEndTrip,
  activeRoute,
  currentSpeed = 0,
  currentRoadName = "Bengaluru Road",
  destinationName = "Destination",
  hasRoutes = false,
  selectedRouteIndex = 0,
  onSelectRouteIndex,
  routesList = [],
}) {
  const formatDuration = (seconds) => {
    if (!seconds) return "--";
    const mins = Math.round(seconds / 60);
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    if (hrs > 0) return `${hrs} hr ${remMins} min`;
    return `${remMins} min`;
  };

  const formatDistance = (meters) => {
    if (!meters) return "--";
    if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
    return `${Math.round(meters)} m`;
  };

  return (
    <div className="nav-stats-card">
      {/* Route Selector Chips if routes available and trip not started */}
      {tripStatus === "inactive" && hasRoutes && routesList.length > 1 && (
        <div className="route-options-chips">
          {routesList.map((rt, idx) => (
            <button
              key={idx}
              className={`route-chip ${idx === selectedRouteIndex ? "is-selected" : ""}`}
              onClick={() => onSelectRouteIndex(idx)}
            >
              <span className="chip-badge">{idx === 0 ? "Fastest" : `Alt ${idx}`}</span>
              <span className="chip-time">{formatDuration(rt.duration)}</span>
              <span className="chip-dist">{formatDistance(rt.distance)}</span>
            </button>
          ))}
        </div>
      )}

      {/* Historical Safety Context Note */}
      {tripStatus === "inactive" && hasRoutes && (
        <div className="safety-context-note">
          <span className="safety-icon">ℹ️</span>
          <span>Historical safety context available via hotspot layer</span>
        </div>
      )}

      <div className="stats-main-row">
        {/* ETA & Distance */}
        <div className="stat-group primary-stat">
          <div className="stat-value highlight-text">
            {activeRoute ? formatDuration(activeRoute.duration) : "--"}
          </div>
          <div className="stat-sub">
            {activeRoute ? formatDistance(activeRoute.distance) : "No Route"}
          </div>
        </div>

        {/* Speed */}
        <div className="stat-group">
          <div className="stat-value">{Math.round(currentSpeed || 0)}</div>
          <div className="stat-label">km/h</div>
        </div>

        {/* Road & Destination info */}
        <div className="stat-group location-info-group">
          <div className="road-name-title">
            📍 {currentRoadName || "Bengaluru Road"}
          </div>
          <div className="dest-name-sub">
            To: {destinationName || "Selected Destination"}
          </div>
        </div>

        {/* Action Button: Start Trip or End Trip */}
        <div className="trip-action-container">
          {tripStatus === "inactive" ? (
            <button
              className="start-trip-btn"
              onClick={onStartTrip}
              disabled={!hasRoutes}
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M8 5v14l11-7z" />
              </svg>
              <span>START TRIP</span>
            </button>
          ) : (
            <button className="end-trip-btn" onClick={onEndTrip}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M6 6h12v12H6z" />
              </svg>
              <span>END TRIP</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
