import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

export default function MapView({ latitude, longitude, hotspots, onMapClick }) {
  const mapRef = useRef(null);
  const leafletMapRef = useRef(null);
  const queryMarkerRef = useRef(null);
  const hotspotsLayerRef = useRef(null);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!leafletMapRef.current && mapRef.current) {
      const map = L.map(mapRef.current, {
        center: [latitude || 12.9716, longitude || 77.5946],
        zoom: 12,
        zoomControl: false
      });

      L.control.zoom({ position: 'bottomright' }).addTo(map);

      // Dark tiles
      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap &copy; CARTO',
        subdomains: 'abcd',
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

  // Update query marker and map view when lat/lon changes
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (queryMarkerRef.current) {
      map.removeLayer(queryMarkerRef.current);
    }

    const cyanIcon = L.divIcon({
      className: 'custom-leaflet-marker',
      html: `<div style="background: #00f2fe; width: 18px; height: 18px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 0 20px #00f2fe;"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    queryMarkerRef.current = L.marker([latitude, longitude], { icon: cyanIcon }).addTo(map);
    map.flyTo([latitude, longitude], 14, { duration: 1.0 });
  }, [latitude, longitude]);

  // Render accident hotspots markers
  useEffect(() => {
    const layerGroup = hotspotsLayerRef.current;
    if (!layerGroup) return;

    layerGroup.clearLayers();

    const list = hotspots && hotspots.length > 0 ? hotspots : [
      { Station: 'Yelahanka', Latitude: 13.1007, Longitude: 77.5963, Total_Accidents: 1530, Risk_Level: 'VERY HIGH' },
      { Station: 'K R Puram', Latitude: 13.0075, Longitude: 77.6959, Total_Accidents: 1500, Risk_Level: 'VERY HIGH' },
      { Station: 'Kamakshipalya', Latitude: 12.9806, Longitude: 77.5255, Total_Accidents: 1329, Risk_Level: 'HIGH' },
      { Station: 'Peenya', Latitude: 13.0329, Longitude: 77.5273, Total_Accidents: 1201, Risk_Level: 'HIGH' },
      { Station: 'Whitefield', Latitude: 12.9698, Longitude: 77.7499, Total_Accidents: 980, Risk_Level: 'MEDIUM' }
    ];

    list.forEach((h) => {
      const lat = h.Latitude || h.lat;
      const lon = h.Longitude || h.lon;
      const station = h.Station || h.name || 'Station';
      const accidents = h.Total_Accidents || h.acc || 0;
      const risk = h.Risk_Level || h.risk || 'HIGH';

      if (lat && lon) {
        const color = risk === 'VERY HIGH' ? '#ef4444' : risk === 'HIGH' ? '#f97316' : '#f59e0b';
        const circle = L.circleMarker([lat, lon], {
          radius: 8,
          color: color,
          fillColor: color,
          fillOpacity: 0.6
        }).bindPopup(`
          <div style="font-family: sans-serif; padding: 2px;">
            <b style="color: #0f172a;">${station}</b><br/>
            <span>Accidents: <b>${accidents}</b></span><br/>
            <span>Risk Level: <b style="color: ${color};">${risk}</b></span>
          </div>
        `);
        layerGroup.addLayer(circle);
      }
    });
  }, [hotspots]);

  return (
    <section className="map-container-wrapper">
      <div className="map-legend-overlay">
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-low)' }}></div>
          <span>Low (0-30)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-moderate)' }}></div>
          <span>Moderate (31-60)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-high)' }}></div>
          <span>High (61-80)</span>
        </div>
        <div className="legend-item">
          <div className="legend-color" style={{ background: 'var(--risk-very-high)' }}></div>
          <span>Very High (81-100)</span>
        </div>
      </div>

      <div ref={mapRef} className="leaflet-map-element"></div>
    </section>
  );
}
