import React from 'react';
import { ShieldAlert, Cpu } from 'lucide-react';

export default function Header({ isConnected }) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo">
          <ShieldAlert size={24} />
        </div>
        <div>
          <div className="brand-title">Bengaluru Road Safety AI</div>
        </div>
        <span className="brand-badge">Django + React ML</span>
      </div>

      <div className="header-status">
        <div className="status-badge">
          <div className={`status-dot ${isConnected ? 'online' : 'offline'}`}></div>
          <span>{isConnected ? 'Django REST Backend Connected' : 'Offline Evaluation Engine'}</span>
        </div>
        <div className="status-badge">
          <Cpu size={14} style={{ color: '#00f2fe' }} />
          <span>Colab GPU YOLO11s</span>
        </div>
      </div>
    </header>
  );
}
