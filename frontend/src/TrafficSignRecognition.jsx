import "./TrafficSignRecognition.css";

export default function TrafficSignRecognition({ detectedSigns }) {
  const recentSigns = (detectedSigns || []).slice(-5).reverse();

  return (
    <section className="traffic-sign-card">
      <div className="traffic-sign-header">
        <div>
          <h2>🚦 Traffic Signs</h2>
          <p>User-confirmed, unclassified sign regions</p>
        </div>

        <span className="traffic-sign-badge">YOLO11n locator</span>
      </div>

      {recentSigns.length === 0 ? (
        <div className="traffic-sign-empty">
          <span>🚦</span>
          <p>No sign regions confirmed yet</p>
          <small>Detected regions require visual confirmation</small>
        </div>
      ) : (
        <div className="traffic-sign-list">
          {recentSigns.map((sign, index) => (
            <div key={`${sign.timestamp || "sign"}-${index}`} className="traffic-sign-item">
              <div className="traffic-sign-info">
                <strong>{sign.sign_name || "Unknown Sign"}</strong>
                <small>
                  {sign.timestamp
                    ? new Date(sign.timestamp).toLocaleTimeString()
                    : "Just now"}
                </small>
              </div>

              <span className="traffic-sign-confidence">
                {typeof sign.confidence === "number"
                  ? `${sign.confidence.toFixed(1)}%`
                  : sign.confidence || "N/A"}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
