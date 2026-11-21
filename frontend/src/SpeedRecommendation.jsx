import { useState, useEffect } from "react";
import "./SpeedRecommendation.css";

export default function SpeedRecommendation({
  roadDamageDetections = [],
  trafficSignDetections = [],
  trafficData = null,
  weatherData = null,
  currentSpeed = 0,
}) {
  const [recommendedSpeed, setRecommendedSpeed] = useState(null);
  const [riskFactors, setRiskFactors] = useState([]);
  const [riskLevel, setRiskLevel] = useState("low");

  useEffect(() => {
    calculateRecommendedSpeed();
  }, [roadDamageDetections, trafficSignDetections, trafficData, weatherData]);

  const calculateRecommendedSpeed = () => {
    let baseSpeed = 60; // Default speed limit in km/h for urban areas
    const factors = [];
    let riskScore = 0;

    // 1. Road Damage Analysis
    if (roadDamageDetections.length > 0) {
      const damageCount = roadDamageDetections.length;
      const damageTypes = new Set(roadDamageDetections.map(d => d.class_name || d.className));
      
      // Potholes and cracks are high risk
      if (damageTypes.has("Pothole") || damageTypes.has("pothole")) {
        baseSpeed = Math.min(baseSpeed, 30);
        factors.push({ type: "road_damage", message: "Potholes detected", severity: "high" });
        riskScore += 30;
      }
      
      if (damageTypes.has("Longitudinal Crack") || damageTypes.has("Transverse Crack")) {
        baseSpeed = Math.min(baseSpeed, 40);
        factors.push({ type: "road_damage", message: "Road cracks detected", severity: "medium" });
        riskScore += 20;
      }
      
      if (damageTypes.has("Alligator Crack")) {
        baseSpeed = Math.min(baseSpeed, 25);
        factors.push({ type: "road_damage", message: "Severe road damage", severity: "high" });
        riskScore += 35;
      }
      
      // Multiple detections reduce speed further
      if (damageCount > 2) {
        baseSpeed = Math.max(baseSpeed - 10, 20);
        factors.push({ type: "road_damage", message: "Multiple road hazards", severity: "high" });
        riskScore += 15;
      }
    }

    // 2. Traffic Sign Analysis
    if (trafficSignDetections.length > 0) {
      trafficSignDetections.forEach(sign => {
        const signName = sign.sign_name || sign.className || "";
        
        // Speed limit signs
        const speedMatch = signName.match(/(\d+)/);
        if (speedMatch) {
          const speedLimit = parseInt(speedMatch[1]);
          baseSpeed = Math.min(baseSpeed, speedLimit);
          factors.push({ type: "traffic_sign", message: `Speed limit: ${speedLimit} km/h`, severity: "medium" });
          riskScore += 10;
        }
        
        // Warning signs
        if (signName.toLowerCase().includes("warning") || signName.toLowerCase().includes("caution")) {
          baseSpeed = Math.max(baseSpeed - 15, 20);
          factors.push({ type: "traffic_sign", message: "Warning sign detected", severity: "high" });
          riskScore += 25;
        }
        
        // Stop signs
        if (signName.toLowerCase().includes("stop")) {
          baseSpeed = 0;
          factors.push({ type: "traffic_sign", message: "Stop sign ahead", severity: "critical" });
          riskScore += 50;
        }
        
        // School zone
        if (signName.toLowerCase().includes("school")) {
          baseSpeed = Math.min(baseSpeed, 25);
          factors.push({ type: "traffic_sign", message: "School zone", severity: "high" });
          riskScore += 30;
        }
      });
    }

    // 3. Traffic Conditions
    if (trafficData && trafficData.current_speed_kmh && trafficData.free_flow_speed_kmh) {
      const currentSpeed = trafficData.current_speed_kmh;
      const freeFlowSpeed = trafficData.free_flow_speed_kmh;
      const speedReduction = ((freeFlowSpeed - currentSpeed) / freeFlowSpeed) * 100;
      
      if (speedReduction > 50) {
        baseSpeed = Math.min(baseSpeed, currentSpeed);
        factors.push({ type: "traffic", message: "Heavy congestion", severity: "high" });
        riskScore += 25;
      } else if (speedReduction > 30) {
        baseSpeed = Math.min(baseSpeed, currentSpeed + 10);
        factors.push({ type: "traffic", message: "Moderate congestion", severity: "medium" });
        riskScore += 15;
      } else if (speedReduction > 15) {
        baseSpeed = Math.min(baseSpeed, currentSpeed + 15);
        factors.push({ type: "traffic", message: "Light congestion", severity: "low" });
        riskScore += 5;
      }
    }

    // 4. Weather Conditions
    if (weatherData) {
      const weatherCode = weatherData.weather_code;
      const rain = weatherData.rain || 0;
      const windSpeed = weatherData.wind_speed || 0;
      
      // Rain conditions
      if (rain > 5) {
        baseSpeed = Math.max(baseSpeed - 20, 20);
        factors.push({ type: "weather", message: "Heavy rain", severity: "high" });
        riskScore += 30;
      } else if (rain > 0) {
        baseSpeed = Math.max(baseSpeed - 10, 30);
        factors.push({ type: "weather", message: "Light rain", severity: "medium" });
        riskScore += 15;
      }
      
      // Weather codes for bad conditions
      if (weatherCode >= 61 && weatherCode <= 67) { // Rain
        baseSpeed = Math.max(baseSpeed - 15, 25);
        factors.push({ type: "weather", message: "Rainy conditions", severity: "medium" });
        riskScore += 20;
      }
      
      if (weatherCode >= 71 && weatherCode <= 77) { // Snow
        baseSpeed = Math.max(baseSpeed - 30, 15);
        factors.push({ type: "weather", message: "Snow conditions", severity: "high" });
        riskScore += 40;
      }
      
      if (weatherCode === 45 || weatherCode === 48) { // Fog
        baseSpeed = Math.max(baseSpeed - 25, 20);
        factors.push({ type: "weather", message: "Foggy conditions", severity: "high" });
        riskScore += 35;
      }
      
      if (weatherCode >= 95) { // Thunderstorm
        baseSpeed = Math.max(baseSpeed - 35, 15);
        factors.push({ type: "weather", message: "Thunderstorm", severity: "critical" });
        riskScore += 50;
      }
      
      // High wind
      if (windSpeed > 50) {
        baseSpeed = Math.max(baseSpeed - 10, 30);
        factors.push({ type: "weather", message: "High winds", severity: "medium" });
        riskScore += 15;
      }
    }

    // Ensure minimum speed is reasonable
    baseSpeed = Math.max(baseSpeed, 0);

    setRecommendedSpeed(Math.round(baseSpeed));
    setRiskFactors(factors);

    // Determine overall risk level
    if (riskScore >= 60) {
      setRiskLevel("critical");
    } else if (riskScore >= 40) {
      setRiskLevel("high");
    } else if (riskScore >= 20) {
      setRiskLevel("medium");
    } else {
      setRiskLevel("low");
    }
  };

  const getRiskColor = () => {
    switch (riskLevel) {
      case "critical": return "#dc2626";
      case "high": return "#f97316";
      case "medium": return "#eab308";
      case "low": return "#22c55e";
      default: return "#64748b";
    }
  };

  const getSpeedAdvice = () => {
    if (recommendedSpeed === null) return "Analyzing conditions...";
    
    if (recommendedSpeed === 0) return "STOP - Hazard ahead";
    
    if (currentSpeed > recommendedSpeed + 10) {
      return "SLOW DOWN - Reduce speed immediately";
    }
    
    if (currentSpeed > recommendedSpeed + 5) {
      return "Reduce speed slightly";
    }
    
    if (currentSpeed < recommendedSpeed - 10) {
      return "Speed up safely";
    }
    
    return "Maintain current speed";
  };

  const speedDifference = recommendedSpeed !== null ? currentSpeed - recommendedSpeed : null;

  return (
    <div className="speed-recommendation-card">
      <div className="speed-header">
        <h3>⚡ Safe Speed Advisor</h3>
        <div className={`risk-indicator risk-${riskLevel}`}>
          {riskLevel.toUpperCase()}
        </div>
      </div>

      <div className="speed-display">
        <div className="recommended-speed">
          <span className="speed-label">Recommended</span>
          <span className="speed-value" style={{ color: getRiskColor() }}>
            {recommendedSpeed !== null ? `${recommendedSpeed}` : "--"}
          </span>
          <span className="speed-unit">km/h</span>
        </div>

        <div className="current-speed">
          <span className="speed-label">Current</span>
          <span className="speed-value">{Math.round(currentSpeed)}</span>
          <span className="speed-unit">km/h</span>
        </div>
      </div>

      <div className="speed-advice">
        <span className="advice-icon">
          {speedDifference > 10 ? "⚠️" : speedDifference > 5 ? "🔶" : speedDifference < -10 ? "🟢" : "✅"}
        </span>
        <span className="advice-text">{getSpeedAdvice()}</span>
      </div>

      {riskFactors.length > 0 && (
        <div className="risk-factors">
          <div className="factors-title">Risk Factors:</div>
          {riskFactors.map((factor, idx) => (
            <div key={idx} className={`factor-item factor-${factor.severity}`}>
              <span className="factor-icon">
                {factor.type === "road_damage" ? "🛣️" : 
                 factor.type === "traffic_sign" ? "🛑" : 
                 factor.type === "traffic" ? "🚦" : "🌦️"}
              </span>
              <span className="factor-message">{factor.message}</span>
            </div>
          ))}
        </div>
      )}

      {riskFactors.length === 0 && recommendedSpeed !== null && (
        <div className="no-risks">
          <span className="no-risks-icon">✅</span>
          <span>Road conditions are favorable</span>
        </div>
      )}
    </div>
  );
}
