import React from 'react';
import { ShieldAlert, ShieldCheck, Activity, CloudSun, AlertTriangle, Gauge, Eye } from 'lucide-react';

export default function ResultsPanel({ result }) {
  const assessment = result?.assessment || {
    risk_score: 65.0,
    risk_level: 'HIGH RISK',
    travel_speed_kmh: 70,
    recommended_safe_speed: 40,
    recommendation: 'Exercise extra caution. Moderate to high congestion and road surface damage detected.'
  };

  const roadCond = result?.road_condition || {
    surface_status: 'Severe Potholes & Cracks',
    surface_damage_level: 65.0,
    junction_complexity: 'Moderate',
    traffic_flow: '35 km/h flow',
    illumination: 'Good Night Lighting',
    weather: 'Clear (23.0°C)'
  };

  const hazards = result?.safety_hazards || result?.contributing_factors || [
    'High-risk historical accident corridor (1,530+ accidents in area)',
    'Severe road surface degradation & deep potholes detected',
    'Driving 70 km/h over recommended 40 km/h safe limit'
  ];

  const score = typeof assessment.risk_score === 'number' ? assessment.risk_score : parseFloat(assessment.risk_score || 0);
  const level = assessment.risk_level || 'LOW RISK';

  let color = 'var(--risk-low)';
  if (level.includes('SEVERE') || level.includes('VERY HIGH')) color = 'var(--risk-very-high)';
  else if (level.includes('HIGH')) color = 'var(--risk-high)';
  else if (level.includes('MODERATE')) color = 'var(--risk-moderate)';

  return (
    <aside className="card-panel">
      <div className="panel-header">
        <ShieldAlert size={18} />
        <span>Road Safety & Condition Analysis</span>
      </div>

      {/* Circular Safety Risk Gauge */}
      <div className="risk-gauge-container">
        <div
          className="risk-circle"
          style={{
            borderColor: color,
            boxShadow: `0 0 35px ${color}`
          }}
        >
          <div className="risk-score-num" style={{ color: '#ffffff' }}>
            {score.toFixed(1)}
          </div>
          <div className="risk-level-badge" style={{ color: color }}>
            {level}
          </div>
        </div>
      </div>

      {/* Safety Recommendation Banner */}
      <div className="metric-box" style={{ borderLeft: `3px solid ${color}` }}>
        <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <ShieldCheck size={13} style={{ color: color }} />
          Driver Advisory & Action
        </div>
        <div style={{ fontSize: '0.82rem', color: '#f1f5f9', marginTop: '0.25rem', lineHeight: '1.4' }}>
          {assessment.recommendation}
        </div>
      </div>

      {/* Driver Metrics Grid */}
      <div className="metrics-grid-2x2">
        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <AlertTriangle size={12} style={{ color: '#00f2fe' }} />
            Road Surface
          </div>
          <div className="metric-value" style={{ fontSize: '0.85rem' }}>
            {roadCond.surface_status}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Gauge size={12} style={{ color: '#00f2fe' }} />
            Safe Speed
          </div>
          <div className="metric-value" style={{ fontSize: '0.85rem' }}>
            {assessment.travel_speed_kmh} km/h (Safe: {assessment.recommended_safe_speed || 40} km/h)
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Activity size={12} style={{ color: '#00f2fe' }} />
            Traffic Flow
          </div>
          <div className="metric-value" style={{ fontSize: '0.85rem' }}>
            {roadCond.traffic_flow}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Eye size={12} style={{ color: '#00f2fe' }} />
            Lighting & Weather
          </div>
          <div className="metric-value" style={{ fontSize: '0.85rem' }}>
            {roadCond.illumination}
          </div>
        </div>
      </div>

      {/* Key Road Hazards & Safety Drivers */}
      <div className="form-group">
        <label className="form-label">Key Road Safety Drivers & Hazards:</label>
        <ul className="factors-list">
          {hazards.map((hazard, idx) => (
            <li key={idx} className="factor-item">
              <AlertTriangle size={13} style={{ color: '#f59e0b', flexShrink: 0 }} />
              <span>{hazard}</span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

