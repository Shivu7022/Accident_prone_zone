import React from "react";
import "./MLDetectionHUD.css";

export default function MLDetectionHUD({ recentDetections = [] }) {
  if (!recentDetections || recentDetections.length === 0) return null;

  return (
    <div className="ml-hud-container">
      {recentDetections.slice(0, 3).map((det, idx) => (
        <div
          key={det.id || idx}
          className={`ml-hud-card ${det.type === "road_damage" ? "damage-hud" : "sign-hud"}`}
        >
          <div className="hud-badge">
            {det.type === "road_damage" ? "⚠️ ROAD DAMAGE" : "🛑 TRAFFIC SIGN"}
          </div>

          <div className="hud-title">{det.className || det.sign_name || "Detected Hazard"}</div>

          <div className="hud-metrics">
            <span className="metric-conf">
              Conf: <strong>{det.confidence}%</strong>
            </span>
            {det.inference_ms && (
              <span className="metric-latency">{det.inference_ms} ms</span>
            )}
          </div>

          {det.annotated_image && (
            <img
              src={det.annotated_image}
              alt="ML Detection"
              className="hud-thumbnail"
            />
          )}
        </div>
      ))}
    </div>
  );
}
