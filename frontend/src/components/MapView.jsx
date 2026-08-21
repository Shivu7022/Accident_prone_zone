import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Layers, MapPin } from 'lucide-react';

const TILE_SERVERS = {
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap &copy; CARTO'
  },
  street: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors'
  }
};

export default function MapView({ latitude, longitude, hotspots, onMapClick, address }) {
  const mapRef = useRef(null);
  const leafletMapRef = useRef(null);
  const queryMarkerRef = useRef(null);
  const hotspotsLayerRef = useRef(null);
  const tileLayerRef = useRef(null);
  const [mapStyle, setMapStyle] = useState('dark');

  // Initialize Leaflet Map
  useEffect(() => {
    if (!leafletMapRef.current && mapRef.current) {
      const map = L.map(mapRef.current, {
        center: [latitude || 12.9716, longitude || 77.5946],
        zoom: 13,
        zoomControl: false
      });

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      // Default Dark Tiles
      tileLayerRef.current = L.tileLayer(TILE_SERVERS.dark.url, {
        attribution: TILE_SERVERS.dark.attribution,
        maxZoom: 19
      }).addTo(map);

      hotspotsLayerRef.current = L.layerGroup().addTo(map);

      map.on('click', (e) => {
        if (onMapClick) {
          onMapClick(e.latlng.lat, e.latlng.lng);
        }
      });

      leafletMapRef.current = map;
    }
  }, []);

  // Toggle Map Style (Dark / Street Map)
  const toggleMapStyle = () => {
    const nextStyle = mapStyle === 'dark' ? 'street' : 'dark';
    setMapStyle(nextStyle);
    if (leafletMapRef.current && tileLayerRef.current) {
      leafletMapRef.current.removeLayer(tileLayerRef.current);
      tileLayerRef.current = L.tileLayer(TILE_SERVERS[nextStyle].url, {
        attribution: TILE_SERVERS[nextStyle].attribution,
        maxZoom: 19
      }).addTo(leafletMapRef.current);
    }
  };

  // Update query marker and map view when lat/lon changes
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (queryMarkerRef.current) {
      map.removeLayer(queryMarkerRef.current);
    }

    const cyanIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `
        <div style="position: relative; display: flex; align-items: center; justify-content: center;">
          <div style="position: absolute; width: 34px; height: 34px; border-radius: 50%; background: rgba(0, 242, 254, 0.3); animation: pulse 2s infinite;"></div>
          <div style="background: #00f2fe; width: 18px; height: 18px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 0 20px #00f2fe; z-index: 2;"></div>
        </div>
      `,
      iconSize: [34, 34],
      iconAnchor: [17, 17]
    });

    const marker = L.marker([latitude, longitude], { icon: cyanIcon }).addTo(map);
    marker.bindPopup(`
      <div style="font-family: sans-serif; padding: 4px; color: #0f172a; min-width: 160px;">
        <b style="font-size: 0.9rem;">Selected Safety Query Pin</b><br/>
        <span style="font-size: 0.78rem; color: #475569;">${address || `${latitude.toFixed(4)}°N, ${longitude.toFixed(4)}°E`}</span>
      </div>
    `);

    queryMarkerRef.current = marker;
    map.flyTo([latitude, longitude], 14, { duration: 1.0 });
  }, [latitude, longitude, address]);

  // Render accident hotspots markers
  useEffect(() => {
    const layerGroup = hotspotsLayerRef.current;
    if (!layerGroup) return;

    layerGroup.clearLayers();

    const list = hotspots && hotspots.length > 0 ? hotspots : [
      { Station: 'Yelahanka Corridor', Latitude: 13.1007, Longitude: 77.5963, Total_Accidents: 1530, Risk_Level: 'SEVERE HAZARD' },
      { Station: 'K R Puram Junction', Latitude: 13.0075, Longitude: 77.6959, Total_Accidents: 1500, Risk_Level: 'SEVERE HAZARD' },
      { Station: 'Kamakshipalya Zone', Latitude: 12.9806, Longitude: 77.5255, Total_Accidents: 1329, Risk_Level: 'HIGH RISK' },
      { Station: 'Peenya Industrial Road', Latitude: 13.0329, Longitude: 77.5273, Total_Accidents: 1201, Risk_Level: 'HIGH RISK' },
      { Station: 'Whitefield Main Road', Latitude: 12.9698, Longitude: 77.7499, Total_Accidents: 980, Risk_Level: 'MODERATE RISK' }
    ];

    list.forEach((h) => {
      const lat = h.Latitude || h.lat;
      const lon = h.Longitude || h.lon;
      const station = h.Station || h.name || 'Accident Prone Area';
      const accidents = h.Total_Accidents || h.acc || 0;
      const risk = h.Risk_Level || h.risk || 'HIGH RISK';

      if (lat && lon) {
        const color = risk.includes('SEVERE') || risk === 'VERY HIGH' ? '#ef4444' : risk.includes('HIGH') ? '#f97316' : '#f59e0b';
        const circle = L.circleMarker([lat, lon], {
          radius: 9,
          color: color,
          fillColor: color,
          fillOpacity: 0.65,
          weight: 2
        }).bindPopup(`
          <div style="font-family: sans-serif; padding: 4px;">
            <b style="color: #0f172a; font-size: 0.88rem;">${station}</b><br/>
            <span style="font-size: 0.8rem; color: #334155;">Historical Accidents: <b style="color: #0f172a;">${accidents}</b></span><br/>
            <span style="font-size: 0.8rem; color: #334155;">Safety Status: <b style="color: ${color};">${risk}</b></span>
          </div>
        `);
        layerGroup.addLayer(circle);
      }
    });
  }, [hotspots]);

  return (
    <section className="map-container-wrapper">
      {/* Map Header Overlay */}
      <div className="map-header-overlay">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#fff', fontSize: '0.85rem', fontWeight: 600 }}>
          <MapPin size={15} style={{ color: '#00f2fe' }} />
          <span>Interactive Real-World Safety Map (Click anywhere to inspect road safety)</span>
        </div>
        <button className="preset-btn" onClick={toggleMapStyle} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem' }}>
          <Layers size={13} />
          <span>{mapStyle === 'dark' ? 'Street View' : 'Dark Mode'}</span>
        </button>
      </div>

      {/* Map Legend Overlay */}
      <div className="map-legend-overlay">
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-low)' }}></div>
          <span>Low Risk</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-moderate)' }}></div>
          <span>Moderate Risk</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-high)' }}></div>
          <span>High Risk</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-very-high)' }}></div>
          <span>Severe Hazard</span>
        </div>
      </div>

      <div ref={mapRef} className="leaflet-map-element"></div>
    </section>
  );
}

