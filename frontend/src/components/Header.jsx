import React from 'react';
import { ShieldAlert, Navigation } from 'lucide-react';

export default function Header({ isConnected }) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo">
          <ShieldAlert size={24} />
        </div>
        <div>
          <div className="brand-title">Bengaluru Road Safety & Navigation AI</div>
        </div>
        <span className="brand-badge">Live Safety Map</span>
      </div>

      <div className="header-status">
        <div className="status-badge">
          <div className={`status-dot ${isConnected ? 'online' : 'offline'}`}></div>
          <span>{isConnected ? 'Real-Time Safety Engine Active' : 'Offline Mode'}</span>
        </div>
        <div className="status-badge">
          <Navigation size={14} style={{ color: '#00f2fe' }} />
          <span>Road Condition Intelligence</span>
        </div>
      </div>
    </header>
  );
}

