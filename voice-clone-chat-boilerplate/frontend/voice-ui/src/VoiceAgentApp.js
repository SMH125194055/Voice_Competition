import React, { useState } from 'react';
import './App.css';
import RealTimeVoiceAgent from './components/RealTimeVoiceAgent';
import VADVoiceAgent from './components/VADVoiceAgent';
import LargeVideoAgent from './components/LargeVideoAgent';
import MeetingAgent from './components/MeetingAgent';
import ParallelPipelineAgent from './components/ParallelPipelineAgent';
import App from './App';

const VoiceAgentApp = () => {
  const [mode, setMode] = useState('parallel'); // 'meeting', 'realtime', 'vad', 'large-video', 'parallel', or 'history'

  return (
    <div>
      {/* Mode Switcher */}
      <div style={{
        position: 'fixed',
        top: '1rem',
        right: '1rem',
        zIndex: 1000,
        display: 'flex',
        gap: '0.5rem',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={() => setMode('meeting')}
          style={{
            padding: '0.8rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            background: mode === 'meeting' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'rgba(255,255,255,0.2)',
            color: 'white',
            fontWeight: '600',
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease'
          }}
        >
          🎥 Meeting
        </button>
        <button
          onClick={() => setMode('large-video')}
          style={{
            padding: '0.8rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            background: mode === 'large-video' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'rgba(255,255,255,0.2)',
            color: 'white',
            fontWeight: '600',
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease'
          }}
        >
          🎬 Large Video
        </button>
        <button
          onClick={() => setMode('parallel')}
          style={{
            padding: '0.8rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            background: mode === 'parallel' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : 'rgba(255,255,255,0.2)',
            color: 'white',
            fontWeight: '600',
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease'
          }}
        >
          ⚡ Parallel Pipeline
        </button>
        <button
          onClick={() => setMode('vad')}
          style={{
            padding: '0.8rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            background: mode === 'vad' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'rgba(255,255,255,0.2)',
            color: 'white',
            fontWeight: '600',
            cursor: 'pointer',
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease'
          }}
        >
          🎯 VAD Agent
        </button>
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
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease'
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
            boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
            transition: 'all 0.3s ease'
          }}
        >
          💬 History
        </button>
      </div>

      {/* Render ONLY Active Mode (prevents multiple VAD instances) */}
      {mode === 'meeting' && <MeetingAgent />}
      {mode === 'large-video' && <LargeVideoAgent />}
      {mode === 'parallel' && <ParallelPipelineAgent />}
      {mode === 'vad' && <VADVoiceAgent />}
      {mode === 'realtime' && <RealTimeVoiceAgent />}
      {mode === 'history' && <App />}
    </div>
  );
};

export default VoiceAgentApp;

