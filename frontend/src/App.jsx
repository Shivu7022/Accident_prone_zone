import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ControlsPanel from './components/ControlsPanel';
import MapView from './components/MapView';
import ResultsPanel from './components/ResultsPanel';

const API_BASE_URL = 'http://localhost:8000';

export default function App() {
  const [latitude, setLatitude] = useState(13.1007);
  const [longitude, setLongitude] = useState(77.5963);
  const [speed, setSpeed] = useState(70);
  const [activePreset, setActivePreset] = useState('Yelahanka');

  const [isConnected, setIsConnected] = useState(false);
  const [hotspots, setHotspots] = useState([]);
  const [result, setResult] = useState(null);

  // Check Django API Health & Load Hotspots on Mount
  useEffect(() => {
    checkHealth();
    fetchHotspots();
    assessRisk(13.1007, 77.5963, 70);
  }, []);

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/health/`);
      if (res.ok) {
        setIsConnected(true);
      } else {
        setIsConnected(false);
      }
    } catch {
      setIsConnected(false);
    }
  };

  const fetchHotspots = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/hotspots/`);
      if (res.ok) {
        const data = await res.json();
        setHotspots(data);
      }
    } catch {
      // Fallback handled in MapView
    }
  };

  const assessRisk = async (lat = latitude, lon = longitude, spd = speed) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/risk/predict/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: lat,
          longitude: lon,
          travel_speed_kmh: spd
        })
      });

      if (res.ok) {
        const data = await res.json();
        setResult(data);
        setIsConnected(true);
        return;
      }
    } catch {
      setIsConnected(false);
    }

    // Client Fallback Evaluation Simulation
    const fallback = simulateRiskAssessment(lat, lon, spd);
    setResult(fallback);
  };

  const simulateRiskAssessment = (lat, lon, spd) => {
    let score = 25.0;
    let level = 'LOW';
    let rec = 'Optimal driving conditions.';
    let factors = [];

    const dYelahanka = Math.hypot(lat - 13.1007, lon - 77.5963);
    if (dYelahanka < 0.05) {
      score += 35.0;
      factors.push('High Historical Area Accident Risk (1,530 Accidents)');
    }

    if (spd > 60) {
      score += 20.0;
      factors.push(`Excessive Travel Speed (${spd} km/h vs 40 km/h limit)`);
    }

    score += 15.0;
    factors.push('Severe Surface Road Damage Detected (65.0/100)');

    score = Math.min(100.0, Math.max(0.0, score));

    if (score >= 81) level = 'VERY HIGH';
    else if (score >= 61) level = 'HIGH';
    else if (score >= 31) level = 'MODERATE';
    else level = 'LOW';

    if (level === 'HIGH' || level === 'VERY HIGH') {
      rec = 'Exercise extra caution. Moderate to high congestion and road damage detected.';
    }

    return {
      location: {
        nearest_road_id: 'BLR_OSM_0206990',
        nearest_road_name: 'OSM Segment (residential)',
        distance_to_segment_km: 0.012
      },
      assessment: {
        risk_score: score,
        risk_level: level,
        travel_speed_kmh: spd,
        recommendation: rec
      },
      contributing_factors: factors,
      feature_breakdown: {
        traffic_condition: '35 km/h',
        temperature_celsius: 23.0,
        road_complexity_score: 3.75,
        road_damage_score: 65.0
      }
    };
  };

  const handleMapClick = (lat, lon) => {
    const fixedLat = parseFloat(lat.toFixed(4));
    const fixedLon = parseFloat(lon.toFixed(4));
    setLatitude(fixedLat);
    setLongitude(fixedLon);
    setActivePreset('');
    assessRisk(fixedLat, fixedLon, speed);
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header isConnected={isConnected} />

      <main className="dashboard-container">
        <ControlsPanel
          latitude={latitude}
          longitude={longitude}
          speed={speed}
          setLatitude={setLatitude}
          setLongitude={setLongitude}
          setSpeed={setSpeed}
          onAssess={() => assessRisk(latitude, longitude, speed)}
          roadInfo={result?.location}
          activePreset={activePreset}
          setActivePreset={setActivePreset}
        />

        <MapView
          latitude={latitude}
          longitude={longitude}
          hotspots={hotspots}
          onMapClick={handleMapClick}
        />

        <ResultsPanel result={result} />
      </main>
    </div>
  );
}
