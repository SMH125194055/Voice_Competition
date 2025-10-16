import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './RealTimeVoiceAgent.css';

const API_BASE_URL = 'http://localhost:8001';

const RealTimeVoiceAgent = () => {
  // State management
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcription, setTranscription] = useState('');
  const [currentResponse, setCurrentResponse] = useState('');
  const [messages, setMessages] = useState([]);
  const [audioLevel, setAudioLevel] = useState(0);
  const [status, setStatus] = useState('Ready to listen...');
  const [vadActive, setVadActive] = useState(false);
  
  // Refs
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const micStreamRef = useRef(null);
  const audioRef = useRef(null);
  const vadTimeoutRef = useRef(null);
  const silenceTimeoutRef = useRef(null);
  const recordingStartTimeRef = useRef(null);
  
  // VAD Configuration
  const SILENCE_THRESHOLD = 30; // Audio level threshold for silence
  const SILENCE_DURATION = 1500; // ms of silence before stopping
  const MIN_RECORDING_DURATION = 1000; // Minimum recording duration
  const SPEECH_THRESHOLD = 40; // Audio level threshold for speech detection
  
  // Initialize audio context for VAD
  useEffect(() => {
    audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);
  
  // Audio level monitoring for VAD
  const monitorAudioLevel = () => {
    if (!analyserRef.current) return;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);
    
    // Calculate average audio level
    const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
    setAudioLevel(average);
    
    // Voice Activity Detection
    if (isListening && !isProcessing) {
      if (average > SPEECH_THRESHOLD) {
        // Speech detected
        setVadActive(true);
        setStatus('Listening...');
        
        // Clear silence timeout
        if (silenceTimeoutRef.current) {
          clearTimeout(silenceTimeoutRef.current);
          silenceTimeoutRef.current = null;
        }
      } else if (average < SILENCE_THRESHOLD) {
        // Silence detected
        if (vadActive && recordingStartTimeRef.current) {
          const recordingDuration = Date.now() - recordingStartTimeRef.current;
          
          // Only stop if we've been recording long enough and have silence
          if (recordingDuration > MIN_RECORDING_DURATION) {
            if (!silenceTimeoutRef.current) {
              silenceTimeoutRef.current = setTimeout(() => {
                console.log('Silence detected, stopping recording...');
                stopListening();
              }, SILENCE_DURATION);
            }
          }
        }
        setStatus('Speak now...');
      }
    }
    
    // Continue monitoring
    if (isListening) {
      requestAnimationFrame(monitorAudioLevel);
    }
  };
  
  // Start listening
  const startListening = async () => {
    try {
      setStatus('Starting microphone...');
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      micStreamRef.current = stream;
      
      // Setup audio analysis for VAD
      const audioContext = audioContextRef.current;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);
      analyserRef.current = analyser;
      
      // Setup MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';
      
      const mediaRecorder = new MediaRecorder(stream, { 
        mimeType,
        audioBitsPerSecond: 128000
      });
      
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        console.log('MediaRecorder stopped, processing audio...');
        await processRecording();
      };
      
      mediaRecorder.start(100); // Request data every 100ms
      recordingStartTimeRef.current = Date.now();
      setIsListening(true);
      setVadActive(false);
      setStatus('Speak now...');
      
      // Start audio level monitoring
      monitorAudioLevel();
      
    } catch (error) {
      console.error('Error starting microphone:', error);
      setStatus('Microphone access denied');
    }
  };
  
  // Stop listening
  const stopListening = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      console.log('Stopping MediaRecorder...');
      mediaRecorderRef.current.stop();
    }
    
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(track => track.stop());
      micStreamRef.current = null;
    }
    
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
    
    setIsListening(false);
    setVadActive(false);
    setAudioLevel(0);
    setStatus('Processing...');
  };
  
  // Process recorded audio
  const processRecording = async () => {
    const recordingDuration = Date.now() - recordingStartTimeRef.current;
    console.log(`Recording duration: ${recordingDuration}ms`);
    
    if (audioChunksRef.current.length === 0) {
      console.log('No audio chunks recorded');
      setStatus('No audio detected');
      setTimeout(() => setStatus('Ready to listen...'), 2000);
      return;
    }
    
    const mimeType = mediaRecorderRef.current?.mimeType || 'audio/webm';
    const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
    console.log(`Audio blob created: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
    
    // Check minimum size
    if (audioBlob.size < 2000) {
      console.log('Audio too short');
      setStatus('Recording too short, try again');
      setTimeout(() => setStatus('Ready to listen...'), 2000);
      return;
    }
    
    setIsProcessing(true);
    setStatus('Transcribing...');
    
    try {
      // Step 1: Transcribe audio
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');
      
      const transcribeResponse = await axios.post(`${API_BASE_URL}/transcribe`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const userText = transcribeResponse.data.text;
      setTranscription(userText);
      setStatus('Thinking...');
      
      // Add user message to chat
      const userMessage = {
        id: Date.now(),
        type: 'user',
        text: userText,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, userMessage]);
      
      // Step 2: Get LLM response
      const chatResponse = await axios.post(`${API_BASE_URL}/chat`, {
        message: userText
      });
      
      const aiText = chatResponse.data.reply;
      setCurrentResponse(aiText);
      setStatus('Generating voice...');
      
      // Add AI message to chat
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        text: aiText,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, aiMessage]);
      
      // Step 3: Generate speech with user's voice as reference
      const speakFormData = new FormData();
      speakFormData.append('text', aiText);
      speakFormData.append('reference_audio', audioBlob, 'reference.webm'); // Use user's voice!
      
      const speakResponse = await axios.post(`${API_BASE_URL}/speak`, speakFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob'
      });
      
      // Play the generated audio
      const audioUrl = URL.createObjectURL(speakResponse.data);
      if (audioRef.current) {
        audioRef.current.src = audioUrl;
        setIsSpeaking(true);
        setStatus('Speaking...');
        await audioRef.current.play();
      }
      
      setTranscription('');
      setCurrentResponse('');
      
    } catch (error) {
      console.error('Processing error:', error);
      setStatus('Error: ' + (error.response?.data?.detail || error.message));
      setTimeout(() => setStatus('Ready to listen...'), 3000);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Handle audio playback ended
  const handleAudioEnded = () => {
    setIsSpeaking(false);
    setStatus('Ready to listen...');
  };
  
  // Toggle listening
  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };
  
  // Clear chat history
  const clearChat = () => {
    setMessages([]);
    setTranscription('');
    setCurrentResponse('');
    setStatus('Ready to listen...');
  };
  
  return (
    <div className="realtime-voice-agent">
      {/* Header */}
      <div className="agent-header">
        <div className="agent-title">
          <div className="agent-icon">🎙️</div>
          <h1>AI Voice Assistant</h1>
        </div>
        <button className="clear-btn" onClick={clearChat} disabled={isProcessing}>
          Clear Chat
        </button>
      </div>
      
      {/* Main Voice Interface */}
      <div className="voice-interface">
        {/* Animated Voice Orb */}
        <div className={`voice-orb-container ${isListening ? 'listening' : ''} ${isSpeaking ? 'speaking' : ''} ${vadActive ? 'active' : ''}`}>
          <div className="voice-orb">
            {/* Animated rings */}
            <div className="orb-ring ring-1"></div>
            <div className="orb-ring ring-2"></div>
            <div className="orb-ring ring-3"></div>
            
            {/* Center orb with audio level visualization */}
            <div 
              className="orb-center" 
              style={{ transform: `scale(${1 + (audioLevel / 200)})` }}
            >
              {isListening && <span className="orb-icon">🎤</span>}
              {isSpeaking && <span className="orb-icon">🔊</span>}
              {!isListening && !isSpeaking && <span className="orb-icon">💬</span>}
            </div>
          </div>
          
          {/* Audio level bars */}
          {isListening && (
            <div className="audio-bars">
              {[...Array(20)].map((_, i) => (
                <div 
                  key={i} 
                  className="audio-bar"
                  style={{
                    height: `${Math.max(10, Math.random() * audioLevel * 2)}%`,
                    animationDelay: `${i * 0.05}s`
                  }}
                ></div>
              ))}
            </div>
          )}
        </div>
        
        {/* Status Text */}
        <div className="status-text">
          <p className={vadActive ? 'active' : ''}>{status}</p>
          {isListening && !vadActive && (
            <p className="hint">Start speaking...</p>
          )}
          {vadActive && (
            <p className="hint">I'm listening... (pause to finish)</p>
          )}
        </div>
        
        {/* Real-time Transcription Display */}
        {transcription && (
          <div className="realtime-transcription">
            <span className="transcription-label">You said:</span>
            <p>{transcription}</p>
          </div>
        )}
        
        {/* AI Response Display */}
        {currentResponse && (
          <div className="realtime-response">
            <span className="response-label">AI response:</span>
            <p>{currentResponse}</p>
          </div>
        )}
        
        {/* Control Button */}
        <button 
          className={`control-btn ${isListening ? 'listening' : ''} ${isProcessing ? 'processing' : ''}`}
          onClick={toggleListening}
          disabled={isProcessing || isSpeaking}
        >
          {isProcessing ? (
            <>
              <span className="spinner"></span>
              Processing...
            </>
          ) : isListening ? (
            <>
              <span className="pulse-icon">⏹️</span>
              Stop Recording
            </>
          ) : (
            <>
              <span className="mic-icon">🎤</span>
              Start Talking
            </>
          )}
        </button>
      </div>
      
      {/* Chat Messages Display */}
      <div className="chat-messages">
        <h3>Conversation</h3>
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <p>No messages yet. Start a conversation!</p>
            </div>
          ) : (
            messages.map(message => (
              <div key={message.id} className={`message ${message.type}`}>
                <div className="message-avatar">
                  {message.type === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-content">
                  <div className="message-text">{message.text}</div>
                  <div className="message-time">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Hidden audio element for playback */}
      <audio 
        ref={audioRef} 
        onEnded={handleAudioEnded}
        style={{ display: 'none' }}
      />
    </div>
  );
};

export default RealTimeVoiceAgent;

