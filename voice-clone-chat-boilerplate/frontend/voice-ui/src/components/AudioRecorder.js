import React, { useState, useRef } from 'react';
import './AudioRecorder.css';

const AudioRecorder = ({ onRecordingComplete, disabled, buttonText = "Record Audio" }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioURL, setAudioURL] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const options = { mimeType: 'audio/webm' };
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        // Use the actual MIME type from the recorder
        const mimeType = mediaRecorderRef.current.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(audioBlob);
        setAudioURL(url);
        
        // Notify parent component
        if (onRecordingComplete) {
          onRecordingComplete(audioBlob, url);
        }

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-recorder">
      <div className="recorder-controls">
        {!isRecording ? (
          <button
            className="record-button"
            onClick={startRecording}
            disabled={disabled}
          >
            <span className="record-icon">🎤</span>
            {buttonText}
          </button>
        ) : (
          <button
            className="stop-button"
            onClick={stopRecording}
          >
            <span className="stop-icon">⏹️</span>
            Stop Recording ({formatTime(recordingTime)})
          </button>
        )}
      </div>

      {audioURL && !isRecording && (
        <div className="audio-preview">
          <p className="preview-label">Preview:</p>
          <audio controls src={audioURL} className="audio-player" />
        </div>
      )}
    </div>
  );
};

export default AudioRecorder;

