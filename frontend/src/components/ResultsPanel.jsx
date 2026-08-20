import React from 'react';
import { PieChart, AlertTriangle, ShieldCheck, Activity, CloudSun, GitMerge, AlertCircle } from 'lucide-react';

export default function ResultsPanel({ result }) {
  const assessment = result?.assessment || {
    risk_score: 62.3,
    risk_level: 'HIGH',
    recommendation: 'Exercise extra caution. Moderate to high congestion and road damage detected.'
  };

  const factors = result?.contributing_factors || [
    'High Historical Area Accident Risk (1,530 Accidents)',
    'Severe Surface Road Damage Detected (65.0/100)',
    'Excessive Travel Speed (70 vs 40 km/h limit)'
  ];

  const metrics = result?.feature_breakdown || {
    traffic_condition: '35 km/h',
    weather_condition: 'Clear',
    temperature_celsius: 23.0,
    road_complexity_score: 3.75,
    road_damage_score: 65.0
  };

  const score = typeof assessment.risk_score === 'number' ? assessment.risk_score : parseFloat(assessment.risk_score || 0);
  const level = assessment.risk_level || 'LOW';

  let color = 'var(--risk-low)';
  if (level === 'VERY HIGH') color = 'var(--risk-very-high)';
  else if (level === 'HIGH') color = 'var(--risk-high)';
  else if (level === 'MODERATE') color = 'var(--risk-moderate)';

  return (
    <aside className="card-panel">
      <div className="panel-header">
        <PieChart size={18} />
        <span>Segment Risk Assessment</span>
      </div>

      {/* Circular Risk Gauge */}
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

      {/* Recommendation Banner */}
      <div className="metric-box" style={{ borderLeft: `3px solid ${color}` }}>
        <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
          <ShieldCheck size={12} style={{ color: color }} />
          Safety Recommendation
        </div>
        <div style={{ fontSize: '0.82rem', color: '#f1f5f9', marginTop: '0.2rem', lineHeight: '1.4' }}>
          {assessment.recommendation}
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="metrics-grid-2x2">
        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <Activity size={11} style={{ color: '#00f2fe' }} />
            Traffic
          </div>
          <div className="metric-value">
            {metrics.traffic_condition || `${metrics.congestion_level ? (metrics.congestion_level * 50).toFixed(0) : 35} km/h`}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <CloudSun size={11} style={{ color: '#00f2fe' }} />
            Weather
          </div>
          <div className="metric-value">
            {metrics.temperature_celsius ? `${metrics.temperature_celsius}°C` : '23.0°C'}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <GitMerge size={11} style={{ color: '#00f2fe' }} />
            Complexity
          </div>
          <div className="metric-value">
            {metrics.road_complexity_score ? metrics.road_complexity_score.toFixed(2) : '3.75'}
          </div>
        </div>

        <div className="metric-box">
          <div className="metric-label" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <AlertCircle size={11} style={{ color: '#00f2fe' }} />
            Damage
          </div>
          <div className="metric-value">
            {metrics.road_damage_score ? metrics.road_damage_score.toFixed(1) : '65.0'}
          </div>
        </div>
      </div>

      {/* SHAP Factors */}
      <div className="form-group">
        <label className="form-label">Model Contributing Factors (SHAP Explanation):</label>
        <ul className="factors-list">
          {factors.map((f, idx) => (
            <li key={idx} className="factor-item">
              <AlertTriangle size={13} style={{ color: '#f59e0b', flexShrink: 0 }} />
              <span>{f}</span>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
