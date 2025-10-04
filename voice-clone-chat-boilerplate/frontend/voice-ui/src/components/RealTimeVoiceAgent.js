import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './RealTimeVoiceAgent.css';

const API_BASE_URL = 'http://localhost:8000';

const RealTimeVoiceAgent = () => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [aiResponse, setAiResponse] = useState('');
  const [status, setStatus] = useState('Ready');
  const [referenceVoice, setReferenceVoice] = useState(null);
  const [hasReferenceVoice, setHasReferenceVoice] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const recordingStartTimeRef = useRef(null);
  const recordingStreamRef = useRef(null);
  const recordingTimerRef = useRef(null);

  // Initialize reference voice from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('referenceVoiceBlob');
    if (saved) {
      // Convert base64 back to blob
      fetch(saved).then(res => res.blob()).then(blob => {
        setReferenceVoice(blob);
        setHasReferenceVoice(true);
      });
    }
  }, []);

  // Audio queue player
  const playNextInQueue = async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) {
      return;
    }

    isPlayingRef.current = true;
    setIsSpeaking(true);

    const audioBlob = audioQueueRef.current.shift();
    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    audio.onended = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingRef.current = false;
      
      // Play next chunk if available
      if (audioQueueRef.current.length > 0) {
        playNextInQueue();
      } else {
        setIsSpeaking(false);
        setStatus('Ready');
      }
    };

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl);
      isPlayingRef.current = false;
      setIsSpeaking(false);
      playNextInQueue(); // Try next chunk
    };

    await audio.play();
  };

  // Add audio to queue and start playing
  const queueAudio = (audioBlob) => {
    audioQueueRef.current.push(audioBlob);
    playNextInQueue();
  };

  // Start recording
  const startListening = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      recordingStreamRef.current = stream;
      recordingStartTimeRef.current = Date.now();
      setRecordingDuration(0);
      
      // Update recording duration display every 100ms
      recordingTimerRef.current = setInterval(() => {
        const elapsed = (Date.now() - recordingStartTimeRef.current) / 1000;
        setRecordingDuration(elapsed);
      }, 100);
      
      // Try to use audio/webm for better browser compatibility
      const options = { mimeType: 'audio/webm' };
      mediaRecorderRef.current = new MediaRecorder(stream, options);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          console.log(`Received chunk: ${event.data.size} bytes`);
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = async () => {
        // Clear the recording timer
        if (recordingTimerRef.current) {
          clearInterval(recordingTimerRef.current);
          recordingTimerRef.current = null;
        }
        
        // Check minimum recording duration
        const recordingDuration = Date.now() - recordingStartTimeRef.current;
        
        // Increased minimum to 1000ms (1 second) for valid WebM
        if (recordingDuration < 1000) {
          setStatus('⚠️ Too short! Hold for at least 1.5 seconds');
          stream.getTracks().forEach(track => track.stop());
          setTimeout(() => setStatus('Ready'), 2500);
          setRecordingDuration(0);
          return;
        }
        
        // Use the actual MIME type from the recorder
        const mimeType = mediaRecorderRef.current.mimeType || 'audio/webm';
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        
        console.log(`Recording complete: ${recordingDuration}ms, Blob size: ${audioBlob.size} bytes, Chunks: ${audioChunksRef.current.length}`);
        
        // Increased minimum size to 2000 bytes for valid WebM
        if (audioBlob.size < 2000) {
          setStatus('⚠️ Recording failed - no audio captured. Check microphone!');
          stream.getTracks().forEach(track => track.stop());
          setTimeout(() => setStatus('Ready'), 3000);
          setRecordingDuration(0);
          return;
        }
        
        stream.getTracks().forEach(track => track.stop());
        setRecordingDuration(0);
        
        // Process the recorded audio
        await processVoiceInput(audioBlob);
      };

      // Request data every 100ms to ensure we capture audio chunks
      mediaRecorderRef.current.start(100);
      setIsListening(true);
      setStatus('🎤 Recording...');
    } catch (error) {
      console.error('Microphone error:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  // Stop recording
  const stopListening = () => {
    if (mediaRecorderRef.current && isListening) {
      // Clear the timer
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      // Check if recording duration is sufficient
      const recordingDuration = Date.now() - recordingStartTimeRef.current;
      
      // Increased minimum to 1000ms (1 second)
      if (recordingDuration < 1000) {
        // Too short, cancel the recording
        if (mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
        }
        if (recordingStreamRef.current) {
          recordingStreamRef.current.getTracks().forEach(track => track.stop());
        }
        setIsListening(false);
        setRecordingDuration(0);
        setStatus('⚠️ Hold button for at least 1.5 seconds!');
        setTimeout(() => setStatus('Ready'), 2500);
        return;
      }
      
      mediaRecorderRef.current.stop();
      setIsListening(false);
    }
  };

  // Process voice input through full pipeline
  const processVoiceInput = async (audioBlob) => {
    if (!hasReferenceVoice) {
      alert('Please set up your voice first!');
      setStatus('Ready');
      return;
    }

    setIsProcessing(true);
    setTranscript('');
    setAiResponse('');

    try {
      // Step 1: Transcribe
      setStatus('Understanding...');
      const formData = new FormData();
      formData.append('audio', audioBlob, 'question.wav');

      const transcribeResponse = await axios.post(
        `${API_BASE_URL}/transcribe`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      
      const userText = transcribeResponse.data.text;
      setTranscript(userText);

      // Step 2: Get AI response
      setStatus('Thinking...');
      const chatResponse = await axios.post(
        `${API_BASE_URL}/chat`,
        { message: userText },
        { headers: { 'Content-Type': 'application/json' } }
      );
      
      const replyText = chatResponse.data.reply;
      setAiResponse(replyText);

      // Step 3: Generate voice (and stream if possible)
      setStatus('Speaking...');
      
      const speakFormData = new FormData();
      speakFormData.append('text', replyText);
      if (referenceVoice) {
        speakFormData.append('reference_audio', referenceVoice, 'reference.wav');
      }

      const speakResponse = await axios.post(
        `${API_BASE_URL}/speak`,
        speakFormData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          responseType: 'blob'
        }
      );

      // Play the audio
      queueAudio(speakResponse.data);

    } catch (error) {
      console.error('Processing error:', error);
      setStatus('Error: ' + (error.response?.data?.detail || error.message));
    } finally {
      setIsProcessing(false);
    }
  };

  // Setup reference voice
  const setupReferenceVoice = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const options = { mimeType: 'audio/webm' };
      const recorder = new MediaRecorder(stream, options);
      const chunks = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      
      recorder.onstop = () => {
        // Use the actual MIME type from the recorder
        const mimeType = recorder.mimeType || 'audio/webm';
        const blob = new Blob(chunks, { type: mimeType });
        setReferenceVoice(blob);
        setHasReferenceVoice(true);
        
        // Save to localStorage as base64
        const reader = new FileReader();
        reader.onloadend = () => {
          localStorage.setItem('referenceVoiceBlob', reader.result);
        };
        reader.readAsDataURL(blob);
        
        stream.getTracks().forEach(track => track.stop());
        alert('Voice set! You can now start talking.');
      };

      recorder.start();
      
      setTimeout(() => {
        recorder.stop();
      }, 5000); // Record 5 seconds

      alert('Recording your voice for 5 seconds...');
      
    } catch (error) {
      console.error('Voice setup error:', error);
      alert('Could not setup voice');
    }
  };

  return (
    <div className="realtime-voice-agent">
      <div className="agent-container">
        {/* Voice Visualizer */}
        <div className={`voice-orb ${isListening ? 'listening' : ''} ${isSpeaking ? 'speaking' : ''} ${isProcessing ? 'processing' : ''}`}>
          <div className="orb-inner">
            {isListening && <span className="icon">🎤</span>}
            {isSpeaking && <span className="icon">🔊</span>}
            {isProcessing && <span className="icon">⚙️</span>}
            {!isListening && !isSpeaking && !isProcessing && <span className="icon">🤖</span>}
          </div>
          <div className="pulse-ring"></div>
          <div className="pulse-ring delayed"></div>
        </div>

        {/* Status */}
        <div className="status-text">{status}</div>

        {/* Transcript Display */}
        {transcript && (
          <div className="transcript-box">
            <strong>You:</strong> {transcript}
          </div>
        )}

        {/* AI Response Display */}
        {aiResponse && (
          <div className="response-box">
            <strong>AI:</strong> {aiResponse}
          </div>
        )}

        {/* Controls */}
        <div className="controls">
          {!hasReferenceVoice ? (
            <button
              className="setup-button"
              onClick={setupReferenceVoice}
            >
              🎙️ Setup My Voice (5s)
            </button>
          ) : (
            <>
              <button
                className={`talk-button ${isListening ? 'active' : ''}`}
                onMouseDown={startListening}
                onMouseUp={stopListening}
                onTouchStart={startListening}
                onTouchEnd={stopListening}
                disabled={isProcessing || isSpeaking}
              >
                {isListening 
                  ? `🎤 Recording... ${recordingDuration.toFixed(1)}s` 
                  : '🎤 Hold to Talk'}
              </button>
              
              <button
                className="reset-button"
                onClick={() => {
                  localStorage.removeItem('referenceVoiceBlob');
                  setHasReferenceVoice(false);
                  setReferenceVoice(null);
                }}
              >
                🔄 Change Voice
              </button>
            </>
          )}
        </div>

        {/* Tips */}
        <div className="tips">
          <p>💡 Hold the button for at least 1.5 seconds while speaking</p>
          <p>⚡ Watch the timer - release after your question is complete</p>
          <p>🎯 AI will respond in your voice</p>
        </div>
      </div>
    </div>
  );
};

export default RealTimeVoiceAgent;

