import React, { useState } from 'react';
import { Sliders, ShieldCheck, MapPin, Search, Crosshair, Navigation } from 'lucide-react';

const PRESETS = [
  { name: 'Yelahanka', lat: 13.1007, lon: 77.5963 },
  { name: 'K R Puram', lat: 13.0075, lon: 77.6959 },
  { name: 'Silk Board', lat: 12.9172, lon: 77.6228 },
  { name: 'Indiranagar', lat: 12.9784, lon: 77.6408 },
  { name: 'Hebbal', lat: 13.0358, lon: 77.5970 },
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
  setActivePreset,
  onLocationSelect
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const handlePresetSelect = (preset) => {
    setLatitude(preset.lat);
    setLongitude(preset.lon);
    setActivePreset(preset.name);
    if (onLocationSelect) {
      onLocationSelect(preset.lat, preset.lon);
    }
  };

  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const res = await fetch(`http://localhost:8000/api/location/search/?q=${encodeURIComponent(searchQuery)}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
        if (data.length > 0) {
          const top = data[0];
          setLatitude(top.lat);
          setLongitude(top.lon);
          setActivePreset('');
          if (onLocationSelect) {
            onLocationSelect(top.lat, top.lon);
          }
        }
      }
    } catch {
      // Fallback geocode
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectSearchResult = (item) => {
    setLatitude(item.lat);
    setLongitude(item.lon);
    setSearchResults([]);
    setSearchQuery(item.display_name.split(',')[0]);
    setActivePreset('');
    if (onLocationSelect) {
      onLocationSelect(item.lat, item.lon);
    }
  };

  const handleLocateMe = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = parseFloat(pos.coords.latitude.toFixed(4));
          const lon = parseFloat(pos.coords.longitude.toFixed(4));
          setLatitude(lat);
          setLongitude(lon);
          setActivePreset('My Location');
          if (onLocationSelect) {
            onLocationSelect(lat, lon);
          }
        },
        () => {
          alert('Location access denied or unavailable.');
        }
      );
    }
  };

  return (
    <aside className="card-panel">
      <div className="panel-header">
        <Sliders size={18} />
        <span>Location & Driving Controls</span>
      </div>

      {/* Real-World Location Search Bar */}
      <form onSubmit={handleSearchSubmit} className="form-group" style={{ position: 'relative' }}>
        <label className="form-label">Search Any Location / Street:</label>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <input
              type="text"
              placeholder="e.g. Silk Board, Indiranagar, MG Road..."
              className="input-control"
              style={{ width: '100%', paddingLeft: '2.2rem', fontFamily: 'inherit' }}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Search size={15} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
          </div>
          <button type="submit" className="preset-btn" style={{ padding: '0 0.8rem', whiteSpace: 'nowrap' }}>
            {isSearching ? '...' : 'Search'}
          </button>
        </div>

        {/* Autocomplete Results Dropdown */}
        {searchResults.length > 0 && (
          <div className="search-dropdown">
            {searchResults.map((item, idx) => (
              <div
                key={idx}
                className="dropdown-item"
                onClick={() => handleSelectSearchResult(item)}
              >
                <MapPin size={13} style={{ color: '#00f2fe', flexShrink: 0 }} />
                <span>{item.display_name}</span>
              </div>
            ))}
          </div>
        )}
      </form>

      {/* Quick Location Presets + Locate Me */}
      <div className="form-group">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label className="form-label">Quick Locations:</label>
          <button
            type="button"
            onClick={handleLocateMe}
            style={{
              background: 'none',
              border: 'none',
              color: '#00f2fe',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem'
            }}
          >
            <Crosshair size={13} />
            Locate Me
          </button>
        </div>

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

      {/* Coordinates */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
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
        <ShieldCheck size={18} />
        <span>Assess Road Safety & Conditions</span>
      </button>

      {/* Real-World Address Card */}
      <div className="metric-box" style={{ marginTop: '0.2rem' }}>
        <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <Navigation size={12} style={{ color: '#00f2fe' }} />
          Identified Location
        </div>
        <div className="metric-value" style={{ fontSize: '0.88rem', color: '#fff', marginTop: '0.3rem', lineHeight: '1.35' }}>
          {roadInfo?.address || 'Gandhinagar, Yelahanka, Bengaluru'}
        </div>
        {roadInfo?.road_type && (
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
            Road Classification: <b style={{ color: '#cbd5e1' }}>{roadInfo.road_type}</b>
          </div>
        )}
      </div>
    </aside>
  );
}

