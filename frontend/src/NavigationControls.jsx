import React from "react";
import "./NavigationControls.css";

export default function NavigationControls({
  onRecenter,
  headingUp,
  onToggleHeadingMode,
  showTraffic,
  onToggleTraffic,
  showHotspots,
  onToggleHotspots,
  showRoadNetwork,
  onToggleRoadNetwork,
  audioEnabled,
  onToggleAudio,
  compassHeading = 0,
}) {
  return (
    <div className="nav-floating-controls">
      {/* Recenter Button */}
      <button
        className="nav-control-btn"
        onClick={onRecenter}
        title="Recenter Map on Location"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm8.94 3A8.994 8.994 0 0013 3.06V1h-2v2.06A8.994 8.994 0 003.06 11H1v2h2.06A8.994 8.994 0 0011 20.94V23h2v-2.06A8.994 8.994 0 0020.94 13H23v-2h-2.06zM12 19c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z" />
        </svg>
      </button>

      {/* Compass / Orientation Toggle */}
      <button
        className={`nav-control-btn ${headingUp ? "is-active" : ""}`}
        onClick={onToggleHeadingMode}
        title={headingUp ? "Switch to North-Up" : "Switch to Heading-Up"}
      >
        <div
          className="compass-needle"
          style={{ transform: `rotate(${-compassHeading}deg)` }}
        >
          ▲
        </div>
      </button>

      {/* Traffic Toggle */}
      <button
        className={`nav-control-btn ${showTraffic ? "is-active" : ""}`}
        onClick={onToggleTraffic}
        title="Toggle TomTom Live Traffic"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M12 2c-4 0-8 3.58-8 8 0 5.25 7.2 11.4 7.6 11.7.2.2.5.3.8.3s.6-.1.8-.3c.4-.3 7.6-6.45 7.6-11.7 0-4.42-4-8-8-8zm0 11c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z" />
        </svg>
      </button>

      {/* Accident Hotspots Toggle */}
      <button
        className={`nav-control-btn ${showHotspots ? "is-active hotspot-btn" : ""}`}
        onClick={onToggleHotspots}
        title="Toggle Historical Accident Hotspots"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M12 2L1 21h22L12 2zm1 14h-2v-2h2v2zm0-4h-2V8h2v4z" />
        </svg>
      </button>

      {/* OSM Roads Overlay Toggle */}
      <button
        className={`nav-control-btn ${showRoadNetwork ? "is-active" : ""}`}
        onClick={onToggleRoadNetwork}
        title="Toggle Bengaluru OSM Road Overlay"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M19 15v-3h-2v3h-3v2h3v3h2v-3h3v-2h-3zM11 3c-4.97 0-9 4.03-9 9 0 4.17 2.84 7.67 6.69 8.64l.81-1.92C5.9 18.06 4 15.25 4 12c0-3.87 3.13-7 7-7s7 3.13 7 7c0 1.25-.33 2.43-.91 3.46l1.54 1.29C19.46 15.34 20 13.73 20 12c0-4.97-4.03-9-9-9z" />
        </svg>
      </button>

      {/* Audio Guidance Toggle */}
      <button
        className={`nav-control-btn ${audioEnabled ? "is-active" : ""}`}
        onClick={onToggleAudio}
        title={audioEnabled ? "Mute Voice Prompts" : "Enable Voice Prompts"}
      >
        {audioEnabled ? (
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73 4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
          </svg>
        )}
      </button>
    </div>
  );
}
