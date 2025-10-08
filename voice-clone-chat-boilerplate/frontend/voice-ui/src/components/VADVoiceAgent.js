import React, { useState, useRef, useEffect } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';
import axios from 'axios';
import './VADVoiceAgent.css';

const API_BASE_URL = 'http://localhost:8000';

const VADVoiceAgent = () => {
  // State management
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [status, setStatus] = useState('Initializing...');
  const [error, setError] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isMuted, setIsMuted] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [currentPhase, setCurrentPhase] = useState('');
  
  // Refs
  const audioRef = useRef(null);
  
  // VAD Configuration  
  const vad = useMicVAD({
    startOnLoad: false,
    modelName: 'silero_vad_v5',
    modelURL: '/vad-models/silero_vad_v5.onnx',
    workletURL: '/vad-models/vad.worklet.bundle.min.js',
    ortConfig: (ort) => {
      ort.env.wasm.wasmPaths = '/';
      ort.env.wasm.numThreads = 1;
      ort.env.wasm.simd = false;
      return {
        executionProviders: ['wasm'],
        logSeverityLevel: 0,
        logVerbosityLevel: 0,
      };
    },
    onSpeechStart: () => {
      console.log('🎤 Speech detected!');
      setIsSpeaking(true);
      setStatus('Listening...');
    },
    onSpeechEnd: (audio) => {
      console.log('🔇 Speech ended, processing...');
      setIsSpeaking(false);
      setStatus('Processing speech...');
      processAudioData(audio);
    },
    onVADMisfire: () => {
      console.log('❌ VAD misfire (false positive)');
      setIsSpeaking(false);
      setStatus('Listening for speech...');
    },
    positiveSpeechThreshold: 0.6,
    negativeSpeechThreshold: 0.5,
    minSpeechFrames: 5,
    redemptionFrames: 8,
    preSpeechPadFrames: 1,
    submitUserSpeechOnPause: true,
  });
  
  // Initialize audio element
  useEffect(() => {
    const audio = new Audio();
    audio.addEventListener('play', () => {
      setIsAISpeaking(true);
      setStatus('AI is speaking...');
    });
    audio.addEventListener('ended', () => {
      setIsAISpeaking(false);
      setStatus(isListening ? 'Listening for speech...' : 'Click Start to begin');
    });
    audio.addEventListener('pause', () => {
      setIsAISpeaking(false);
    });
    audio.addEventListener('error', (e) => {
      console.error('Audio playback error:', e);
      setIsAISpeaking(false);
      setError('Audio playback failed');
    });
    
    audioRef.current = audio;
    
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.removeEventListener('play', () => {});
        audioRef.current.removeEventListener('ended', () => {});
        audioRef.current.removeEventListener('pause', () => {});
        audioRef.current.removeEventListener('error', () => {});
      }
    };
  }, [isListening]);
  
  // Monitor VAD loading state
  useEffect(() => {
    if (vad.loading) {
      setStatus('Loading VAD model...');
      setIsReady(false);
      console.log('🔄 VAD loading...', {
        modelName: 'silero_vad_v5',
        modelURL: '/vad-models/silero_vad_v5.onnx',
        workletURL: '/vad-models/vad.worklet.bundle.min.js',
        wasmPaths: '/',
        threads: 1,
        simd: false
      });
    } else if (vad.errored) {
      setStatus('VAD initialization failed');
      const errorMsg = vad.errored?.message || vad.errored?.toString() || 'Failed to initialize voice detection';
      setError(errorMsg);
      setIsReady(false);
      console.error('❌ VAD Error Details:', {
        error: vad.errored,
        message: errorMsg,
        stack: vad.errored?.stack
      });
    } else {
      setStatus('Ready! Click Start to begin');
      setIsReady(true);
      console.log('✅ VAD initialized successfully!');
    }
  }, [vad.loading, vad.errored]);
  
  // Update listening state
  useEffect(() => {
    setIsListening(vad.listening);
    if (vad.listening && !isProcessing && !isAISpeaking) {
      setStatus('Listening for speech...');
    }
  }, [vad.listening, isProcessing, isAISpeaking]);
  
  // Convert Float32Array to WAV blob
  const float32ArrayToWav = (audioData, sampleRate = 16000) => {
    const numFrames = audioData.length;
    const numChannels = 1;
    const bytesPerSample = 2; // 16-bit
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = numFrames * blockAlign;
    
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);
    
    // Write WAV header
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bytesPerSample * 8, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);
    
    // Convert float32 to int16
    const floatTo16BitPCM = (output, offset, input) => {
      for (let i = 0; i < input.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, input[i]));
        output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      }
    };
    
    floatTo16BitPCM(view, 44, audioData);
    
    return new Blob([buffer], { type: 'audio/wav' });
  };
  
  // Process audio data from VAD
  const processAudioData = async (audioData) => {
    if (isProcessing || isAISpeaking) {
      console.log('⏭️ Skipping - already processing or AI is speaking');
      return;
    }
    
    try {
      setIsProcessing(true);
      setStatus('Converting audio...');
      
      // Convert Float32Array to WAV
      const wavBlob = float32ArrayToWav(audioData);
      console.log('📦 Converted to WAV, size:', wavBlob.size);
      
      if (wavBlob.size < 2000) {
        console.log('⚠️ Audio too short, ignoring');
        setStatus('Listening for speech...');
        setIsProcessing(false);
        return;
      }
      
      // Create File object
      const audioFile = new File([wavBlob], 'speech.wav', { type: 'audio/wav' });
      
      // Send to backend VAD-enhanced endpoint
      await processConversation(audioFile);
      
    } catch (err) {
      console.error('❌ Error processing audio:', err);
      setError(err.message);
      setStatus('Error processing audio');
    } finally {
      setIsProcessing(false);
      if (isListening && !isAISpeaking) {
        setStatus('Listening for speech...');
      }
    }
  };
  
  // Process conversation with backend using streaming
  const processConversation = async (audioFile) => {
    let userText = '';
    let aiText = '';
    
    try {
      setLiveTranscript('');
      setCurrentPhase('transcription');
      setStatus('🎤 Transcribing your speech...');
      
      // Use streaming endpoint
      const formData = new FormData();
      formData.append('audio', audioFile);
      
      const response = await fetch(`${API_BASE_URL}/chat-voice-stream`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        // Decode chunk
        buffer += decoder.decode(value, { stream: true });
        
        // Process Server-Sent Events
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              // Handle different phases
              if (data.phase === 'transcription') {
                if (data.text) {
                  setLiveTranscript(data.text);
                  setStatus(`🎤 "${data.text}"`);
                }
                if (data.status === 'complete' && !data.partial) {
                  userText = data.text;
                  console.log('📝 User said:', userText);
                }
              } else if (data.phase === 'llm') {
                if (data.status === 'started') {
                  setCurrentPhase('llm');
                  setStatus('🤔 AI is thinking...');
                  setLiveTranscript('');
                } else if (data.status === 'complete') {
                  aiText = data.text;
                  setStatus('🎙️ Generating voice...');
                  console.log('🤖 AI replied:', aiText);
                }
              } else if (data.phase === 'tts') {
                if (data.status === 'started') {
                  setCurrentPhase('tts');
                  setStatus('🔊 Generating voice...');
                } else if (data.status === 'complete' && data.audio) {
                  setCurrentPhase('playback');
                  setStatus('🔊 Playing response...');
                  
                  // Decode base64 audio and play
                  const audioData = atob(data.audio);
                  const audioArray = new Uint8Array(audioData.length);
                  for (let i = 0; i < audioData.length; i++) {
                    audioArray[i] = audioData.charCodeAt(i);
                  }
                  const audioBlob = new Blob([audioArray], { type: 'audio/wav' });
                  const audioUrl = URL.createObjectURL(audioBlob);
                  
                  if (!isMuted && audioRef.current) {
                    audioRef.current.src = audioUrl;
                    try {
                      await audioRef.current.play();
                    } catch (playError) {
                      console.error('Playback error:', playError);
                      setIsAISpeaking(false);
                    }
                  }
                }
              } else if (data.status === 'done') {
                console.log('✅ Conversation complete');
                setLiveTranscript('');
                setCurrentPhase('');
                
                // Update conversation history
                if (userText && aiText) {
                  const newMessages = [
                    ...messages,
                    { 
                      id: Date.now(), 
                      type: 'user', 
                      text: userText,
                      timestamp: new Date().toISOString()
                    },
                    { 
                      id: Date.now() + 1, 
                      type: 'ai', 
                      text: aiText,
                      timestamp: new Date().toISOString()
                    }
                  ];
                  setMessages(newMessages);
                }
              } else if (data.status === 'error') {
                throw new Error(data.error || 'Streaming error');
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError);
            }
          }
        }
      }
      
    } catch (err) {
      console.error('❌ Streaming conversation error:', err);
      setError(err.message || 'Failed to process conversation');
      setStatus('Error occurred');
      setLiveTranscript('');
      setCurrentPhase('');
      
      setTimeout(() => {
        setError(null);
        if (isListening) setStatus('Listening for speech...');
      }, 3000);
    }
  };
  
  // Toggle listening
  const toggleListening = () => {
    if (isListening) {
      vad.pause();
      setStatus('Paused');
    } else {
      vad.start();
      setStatus('Listening for speech...');
      setError(null);
    }
  };
  
  // Toggle mute
  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
    }
  };
  
  // Clear conversation
  const clearConversation = () => {
    setMessages([]);
    setError(null);
    setLiveTranscript('');
    setCurrentPhase('');
    setStatus(isListening ? 'Listening for speech...' : 'Ready! Click Start to begin');
  };
  
  return (
    <div className="vad-voice-agent">
      {/* Header */}
      <div className="vad-header">
        <div className="vad-title">
          <div className="vad-icon">🎙️</div>
          <h1>AI Voice Assistant</h1>
          <span className="vad-badge">VAD Enabled</span>
        </div>
        <div className="vad-controls">
          <button 
            className={`mute-btn ${isMuted ? 'muted' : ''}`}
            onClick={toggleMute}
            title={isMuted ? 'Unmute AI' : 'Mute AI'}
          >
            {isMuted ? '🔇' : '🔊'}
          </button>
          <button 
            className="clear-btn" 
            onClick={clearConversation}
            disabled={isProcessing}
          >
            Clear Chat
          </button>
        </div>
      </div>
      
      {/* Main Interface */}
      <div className="vad-main">
        {/* Voice Visualization */}
        <div className={`vad-orb-container ${isSpeaking ? 'user-speaking' : ''} ${isAISpeaking ? 'ai-speaking' : ''} ${isProcessing ? 'processing' : ''}`}>
          {/* User Circle (Left) */}
          <div className="vad-orb user-orb">
            <div className="orb-label">You</div>
            <div className="orb-rings">
              <div className="orb-ring ring-1"></div>
              <div className="orb-ring ring-2"></div>
              <div className="orb-ring ring-3"></div>
            </div>
            <div className={`orb-center ${isSpeaking ? 'active' : ''}`}>
              <span className="orb-emoji">👤</span>
            </div>
          </div>
          
          {/* Connection Line */}
          <div className={`orb-connection ${isProcessing || isAISpeaking ? 'active' : ''}`}>
            <div className="connection-dot dot-1"></div>
            <div className="connection-dot dot-2"></div>
            <div className="connection-dot dot-3"></div>
          </div>
          
          {/* AI Circle (Right) */}
          <div className="vad-orb ai-orb">
            <div className="orb-label">AI Assistant</div>
            <div className="orb-rings">
              <div className="orb-ring ring-1"></div>
              <div className="orb-ring ring-2"></div>
              <div className="orb-ring ring-3"></div>
            </div>
            <div className={`orb-center ${isAISpeaking ? 'active' : ''} ${isProcessing ? 'thinking' : ''}`}>
              {isAISpeaking && <span className="orb-emoji">🔊</span>}
              {isProcessing && !isAISpeaking && (
                <div className="thinking-dots">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              )}
              {!isAISpeaking && !isProcessing && <span className="orb-emoji">🤖</span>}
            </div>
          </div>
        </div>
        
        {/* Live Transcription Display */}
        {liveTranscript && (
          <div className="live-transcript-container">
            <div className="live-transcript-label">
              {currentPhase === 'transcription' && '🎤 Live Transcription:'}
              {currentPhase === 'llm' && '🤔 Processing...'}
              {currentPhase === 'tts' && '🔊 Generating voice...'}
            </div>
            <div className="live-transcript">
              {liveTranscript}
              {currentPhase === 'transcription' && <span className="transcript-cursor">|</span>}
            </div>
          </div>
        )}
        
        {/* Status Display */}
        <div className="vad-status-container">
          <div className={`vad-status ${error ? 'error' : ''} ${isSpeaking ? 'active' : ''}`}>
            {error ? `⚠️ ${error}` : status}
          </div>
          
          {vad.loading && (
            <div className="vad-loading">
              <div className="spinner"></div>
              <span>Loading voice detection model...</span>
            </div>
          )}
        </div>
        
        {/* Control Button */}
        <div className="vad-button-container">
          <button
            className={`vad-main-btn ${isListening ? 'listening' : ''} ${!isReady ? 'disabled' : ''}`}
            onClick={toggleListening}
            disabled={!isReady || vad.loading}
          >
            {isListening ? (
              <>
                <span className="btn-icon">⏹️</span>
                <span className="btn-text">Stop Listening</span>
              </>
            ) : (
              <>
                <span className="btn-icon">🎤</span>
                <span className="btn-text">Start Listening</span>
              </>
            )}
          </button>
          
          {isListening && !isSpeaking && !isProcessing && !isAISpeaking && (
            <p className="vad-hint">💡 Start speaking - I'll detect when you're done</p>
          )}
          {isSpeaking && (
            <p className="vad-hint">🎤 Listening... (pause to finish)</p>
          )}
        </div>
      </div>
      
      {/* Conversation History */}
      <div className="vad-conversation">
        <h3>Conversation History</h3>
        <div className="vad-messages">
          {messages.length === 0 ? (
            <div className="vad-empty-state">
              <div className="empty-icon">💬</div>
              <p>No messages yet</p>
              <p className="empty-hint">
                Click "Start Listening" and speak naturally.<br/>
                The AI will automatically detect when you finish speaking!
              </p>
            </div>
          ) : (
            messages.map(message => (
              <div key={message.id} className={`vad-message ${message.type}`}>
                <div className="message-avatar">
                  {message.type === 'user' ? '👤' : '🤖'}
                </div>
                <div className="message-bubble">
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
      
      {/* Features Info */}
      <div className="vad-features">
        <div className="feature-badge">
          <span className="feature-icon">🎯</span>
          <span className="feature-text">Automatic Speech Detection</span>
        </div>
        <div className="feature-badge">
          <span className="feature-icon">🔇</span>
          <span className="feature-text">Silence Removal</span>
        </div>
        <div className="feature-badge">
          <span className="feature-icon">⚡</span>
          <span className="feature-text">Real-time Processing</span>
        </div>
        <div className="feature-badge">
          <span className="feature-icon">🎤</span>
          <span className="feature-text">Natural Conversation</span>
        </div>
      </div>
      
      {/* Hidden audio element */}
      <audio ref={audioRef} style={{ display: 'none' }} />
    </div>
  );
};

export default VADVoiceAgent;

