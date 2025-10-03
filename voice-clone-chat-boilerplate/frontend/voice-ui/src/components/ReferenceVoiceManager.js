import React, { useState, useRef } from 'react';
import AudioRecorder from './AudioRecorder';
import './ReferenceVoiceManager.css';

const ReferenceVoiceManager = ({ onAudioChange, currentAudioUrl, disabled }) => {
  const [mode, setMode] = useState('record'); // 'record' or 'upload'
  const fileInputRef = useRef(null);

  const handleRecordingComplete = (audioBlob, audioUrl) => {
    onAudioChange(audioBlob, audioUrl);
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('audio/')) {
        alert('Please upload an audio file (WAV, MP3, etc.)');
        return;
      }

      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('File size must be less than 10MB');
        return;
      }

      const url = URL.createObjectURL(file);
      onAudioChange(file, url);
    }
  };

  const handleChangeVoice = () => {
    if (window.confirm('Are you sure you want to change the reference voice? This will affect all future responses.')) {
      onAudioChange(null, null);
    }
  };

  return (
    <div className="reference-voice-manager">
      {!currentAudioUrl ? (
        <>
          {/* Mode Selection */}
          <div className="mode-selector">
            <button
              className={`mode-button ${mode === 'record' ? 'active' : ''}`}
              onClick={() => setMode('record')}
              disabled={disabled}
            >
              🎤 Record
            </button>
            <button
              className={`mode-button ${mode === 'upload' ? 'active' : ''}`}
              onClick={() => setMode('upload')}
              disabled={disabled}
            >
              📁 Upload
            </button>
          </div>

          {/* Recording Mode */}
          {mode === 'record' && (
            <div className="record-mode">
              <AudioRecorder
                onRecordingComplete={handleRecordingComplete}
                disabled={disabled}
                buttonText="Record Reference Voice"
              />
              <p className="hint">
                💡 Tip: Record 3-10 seconds of clear speech
              </p>
            </div>
          )}

          {/* Upload Mode */}
          {mode === 'upload' && (
            <div className="upload-mode">
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
                disabled={disabled}
              />
              <button
                className="upload-button"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled}
              >
                <span className="upload-icon">📁</span>
                Choose Audio File
              </button>
              <p className="hint">
                💡 Supported: WAV, MP3, M4A, OGG (max 10MB)
              </p>
            </div>
          )}
        </>
      ) : (
        /* Reference Voice Set */
        <div className="voice-set">
          <div className="voice-info">
            <span className="check-icon">✅</span>
            <span className="voice-text">Reference voice is set!</span>
          </div>
          
          <audio controls src={currentAudioUrl} className="reference-audio-player" />
          
          <button
            className="change-button"
            onClick={handleChangeVoice}
            disabled={disabled}
          >
            🔄 Change Reference Voice
          </button>
        </div>
      )}
    </div>
  );
};

export default ReferenceVoiceManager;

