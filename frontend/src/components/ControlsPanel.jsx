import React from 'react';
import { Sliders, Zap, MapPin } from 'lucide-react';

const PRESETS = [
  { name: 'Yelahanka', lat: 13.1007, lon: 77.5963 },
  { name: 'K R Puram', lat: 13.0075, lon: 77.6959 },
  { name: 'Peenya', lat: 13.0329, lon: 77.5273 },
  { name: 'Whitefield', lat: 12.9698, lon: 77.7499 },
  { name: 'E-City', lat: 12.8452, lon: 77.6602 },
];

export default function ControlsPanel({
  latitude,
  longitude,
  speed,
  setLatitude,
  setLongitude,
  setSpeed,
  onAssess,
  roadInfo,
  activePreset,
  setActivePreset
}) {
  const handlePresetSelect = (preset) => {
    setLatitude(preset.lat);
    setLongitude(preset.lon);
    setActivePreset(preset.name);
  };

  return (
    <aside className="card-panel">
      <div className="panel-header">
        <Sliders size={18} />
        <span>Location & Travel Speed Query</span>
      </div>

      {/* Quick Preset Picker */}
      <div className="form-group">
        <label className="form-label">Quick Select Bengaluru Location:</label>
        <div className="preset-grid">
          {PRESETS.map((p) => (
            <button
              key={p.name}
              className={`preset-btn ${activePreset === p.name ? 'active' : ''}`}
              onClick={() => handlePresetSelect(p)}
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* Latitude */}
      <div className="form-group">
        <label className="form-label">Latitude (°N)</label>
        <input
          type="number"
          step="0.0001"
          className="input-control"
          value={latitude}
          onChange={(e) => {
            setLatitude(parseFloat(e.target.value) || 0);
            setActivePreset('');
          }}
        />
      </div>

      {/* Longitude */}
      <div className="form-group">
        <label className="form-label">Longitude (°E)</label>
        <input
          type="number"
          step="0.0001"
          className="input-control"
          value={longitude}
          onChange={(e) => {
            setLongitude(parseFloat(e.target.value) || 0);
            setActivePreset('');
          }}
        />
      </div>

      {/* Travel Speed Slider */}
      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label className="form-label">Travel Speed</label>
          <span style={{ fontWeight: 700, color: '#00f2fe', fontFamily: 'Space Grotesk' }}>
            {speed} km/h
          </span>
        </div>
        <input
          type="range"
          min="10"
          max="120"
          value={speed}
          className="range-slider"
          onChange={(e) => setSpeed(parseInt(e.target.value, 10))}
        />
      </div>

      <button className="btn-primary" onClick={onAssess}>
        <Zap size={18} />
        <span>Assess Road Safety Risk</span>
      </button>

      {/* Matched Segment Summary */}
      <div className="metric-box" style={{ marginTop: '0.2rem' }}>
        <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <MapPin size={12} style={{ color: '#00f2fe' }} />
          Matched Master OSM Segment
        </div>
        <div className="metric-value" style={{ fontSize: '0.92rem', color: '#fff' }}>
          {roadInfo ? `${roadInfo.nearest_road_id} (${roadInfo.nearest_road_name})` : 'BLR_OSM_0206990 (Residential)'}
        </div>
        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
          Distance: {roadInfo ? Math.round(roadInfo.distance_to_segment_km * 1000) : 12} meters
        </div>
      </div>
    </aside>
  );
}
