import React, { useState } from 'react';
import './App.css';
import RealTimeVoiceAgent from './components/RealTimeVoiceAgent';
import App from './App';

const VoiceAgentApp = () => {
  const [mode, setMode] = useState('realtime'); // 'realtime' or 'history'

  return (
    <div>
      {/* Mode Switcher */}
      <div style={{
        position: 'fixed',
        top: '1rem',
        right: '1rem',
        zIndex: 1000,
        display: 'flex',
        gap: '0.5rem'
      }}>
        <button
          onClick={() => setMode('realtime')}
          style={{
            padding: '0.8rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            background: mode === 'realtime' ? '#667eea' : 'rgba(255,255,255,0.2)',
            color: 'white',
            fontWeight: '600',
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
          }}
        >
          🎙️ Voice Agent
        </button>
        <button
          onClick={() => setMode('history')}
          style={{
            padding: '0.8rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            background: mode === 'history' ? '#667eea' : 'rgba(255,255,255,0.2)',
            color: 'white',
            fontWeight: '600',
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)'
          }}
        >
          💬 History
        </button>
      </div>

      {/* Render Both Modes (keep mounted to preserve state) */}
      <div style={{ display: mode === 'realtime' ? 'block' : 'none' }}>
        <RealTimeVoiceAgent />
      </div>
      <div style={{ display: mode === 'history' ? 'block' : 'none' }}>
        <App />
      </div>
    </div>
  );
};

export default VoiceAgentApp;

