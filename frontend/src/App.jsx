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
  const [address, setAddress] = useState('Gandhinagar, Yelahanka, Bengaluru');

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

  const fetchAddress = async (lat, lon) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/location/reverse/?lat=${lat}&lon=${lon}`);
      if (res.ok) {
        const data = await res.json();
        if (data.address) {
          setAddress(data.address);
          return data.address;
        }
      }
    } catch {
      // Fallback
    }
    return `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`;
  };

  const assessRisk = async (lat = latitude, lon = longitude, spd = speed) => {
    let currentAddr = address;
    try {
      currentAddr = await fetchAddress(lat, lon);
    } catch {
      // Ignore
    }

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

    // Fallback Client Simulation
    const fallback = simulateRiskAssessment(lat, lon, spd, currentAddr);
    setResult(fallback);
  };

  const simulateRiskAssessment = (lat, lon, spd, addr) => {
    let score = 30.0;
    let level = 'LOW RISK';
    let rec = 'Optimal driving conditions.';
    let hazards = [];

    const dYelahanka = Math.hypot(lat - 13.1007, lon - 77.5963);
    if (dYelahanka < 0.05) {
      score += 35.0;
      hazards.push('High-risk historical accident corridor (1,530+ accidents recorded nearby)');
    }

    if (spd > 60) {
      score += 20.0;
      hazards.push(`Driving ${spd} km/h over recommended 40 km/h safe limit`);
    }

    score += 15.0;
    hazards.push('Moderate to severe surface road damage & potholes detected');

    score = Math.min(100.0, Math.max(0.0, score));

    if (score >= 81) level = 'SEVERE HAZARD';
    else if (score >= 61) level = 'HIGH RISK';
    else if (score >= 31) level = 'MODERATE RISK';
    else level = 'LOW RISK';

    if (level === 'HIGH RISK' || level === 'SEVERE HAZARD') {
      rec = 'Exercise extra caution. Moderate to high congestion and road damage detected.';
    }

    return {
      location: {
        latitude: lat,
        longitude: lon,
        address: addr || `${lat.toFixed(4)}°N, ${lon.toFixed(4)}°E`,
        road_type: 'Primary Road',
        distance_meters: 12
      },
      assessment: {
        risk_score: score,
        risk_level: level,
        travel_speed_kmh: spd,
        recommended_safe_speed: 40,
        recommendation: rec
      },
      road_condition: {
        surface_status: 'Moderate Potholes & Cracks',
        surface_damage_level: 65.0,
        junction_complexity: 'Moderate',
        traffic_flow: '35 km/h flow',
        illumination: 'Good Night Lighting',
        weather: 'Clear (23.0°C)'
      },
      safety_hazards: hazards
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

  const handleLocationSelect = (lat, lon) => {
    assessRisk(lat, lon, speed);
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
          onLocationSelect={handleLocationSelect}
        />

        <MapView
          latitude={latitude}
          longitude={longitude}
          hotspots={hotspots}
          onMapClick={handleMapClick}
          address={result?.location?.address || address}
        />

        <ResultsPanel result={result} />
      </main>
    </div>
  );
}

