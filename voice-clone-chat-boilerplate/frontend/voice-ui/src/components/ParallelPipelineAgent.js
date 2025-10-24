import React, { useState, useRef, useEffect } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';
import './LargeVideoAgent.css';

const API_BASE_URL = 'http://localhost:8000';

const ParallelPipelineAgent = () => {
  // State management
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [status, setStatus] = useState('Initializing...');
  const [error, setError] = useState(null);
  
  // Current conversation states
  const [currentUserText, setCurrentUserText] = useState('');
  const [currentAIText, setCurrentAIText] = useState('');
  const [currentPhase, setCurrentPhase] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [videoProgress, setVideoProgress] = useState({ current: 0, total: 0 });
  const [firstVideoTime, setFirstVideoTime] = useState(null);
  const [pipelineStartTime, setPipelineStartTime] = useState(null);
  
  // Reference settings
  const [referenceVoiceId, setReferenceVoiceId] = useState(null);
  const [referenceVoices, setReferenceVoices] = useState([]);
  const [referencePictureId, setReferencePictureId] = useState(null);
  const [referencePictures, setReferencePictures] = useState([]);
  
  // Refs
  const videoQueueRef = useRef([]);
  const isPlayingVideoRef = useRef(false);
  const abortControllerRef = useRef(null);
  const avatarVideoRef = useRef(null);
  const pipelineMetricsRef = useRef({});
  
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
      setStatus('Recording...');
    },
    onSpeechEnd: (audio) => {
      console.log('✅ Speech ended, processing...');
      processAudioDataParallel(audio);
    },
    onVADMisfire: () => {
      console.log('❌ VAD misfire');
      setStatus('Listening...');
    },
    positiveSpeechThreshold: 0.85,
    negativeSpeechThreshold: 0.65,
    minSpeechFrames: 8,
    redemptionFrames: 10,
    preSpeechPadFrames: 1,
    submitUserSpeechOnPause: true,
  });
  
  // Monitor VAD loading state
  useEffect(() => {
    if (vad.loading) {
      setStatus('Loading voice detection...');
      setIsReady(false);
    } else if (vad.errored) {
      setStatus('Failed to initialize');
      setError('Voice detection failed to load');
      setIsReady(false);
    } else {
      setStatus('Ready to start conversation');
      setIsReady(true);
    }
  }, [vad.loading, vad.errored]);
  
  useEffect(() => {
    setIsListening(vad.listening);
    if (vad.listening && !isProcessing && !isAISpeaking) {
      setStatus('Listening...');
    }
  }, [vad.listening, isProcessing, isAISpeaking]);
  
  // Load reference voices and pictures
  useEffect(() => {
    const loadResources = async () => {
      await loadReferenceVoices();
      await loadReferencePictures();
    };
    loadResources();
  }, []);
  
  const loadReferenceVoices = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/list-reference-voices`);
      const data = await response.json();
      setReferenceVoices(data.voices || []);
      
      if (!referenceVoiceId && data.voices.length > 0) {
        setReferenceVoiceId(data.voices[0].id);
      }
    } catch (error) {
      console.error('Failed to load reference voices:', error);
    }
  };
  
  const loadReferencePictures = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/list-reference-pictures`);
      const data = await response.json();
      setReferencePictures(data.pictures || []);
      
      if (!referencePictureId && data.pictures.length > 0) {
        setReferencePictureId(data.pictures[0].id);
      }
    } catch (error) {
      console.error('Failed to load reference pictures:', error);
    }
  };
  
  // Convert Float32Array to WAV blob
  const float32ArrayToWav = (audioData, sampleRate = 16000) => {
    const numFrames = audioData.length;
    const numChannels = 1;
    const bytesPerSample = 2;
    const blockAlign = numChannels * bytesPerSample;
    const byteRate = sampleRate * blockAlign;
    const dataSize = numFrames * blockAlign;
    
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);
    
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
    
    const volume = 0.8;
    let offset = 44;
    for (let i = 0; i < numFrames; i++) {
      const sample = Math.max(-1, Math.min(1, audioData[i]));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      offset += 2;
    }
    
    return new Blob([buffer], { type: 'audio/wav' });
  };
  
  // Process audio with parallel pipeline
  const processAudioDataParallel = async (audioData) => {
    if (isProcessing || isAISpeaking || isPlayingVideoRef.current) {
      console.log('🚫 Already processing, ignoring new speech');
      return;
    }
    
    try {
      setIsProcessing(true);
      setError(null);
      setCurrentUserText('');
      setCurrentAIText('');
      setCurrentPhase('started');
      setVideoProgress({ current: 0, total: 0 });
      videoQueueRef.current = [];
      pipelineMetricsRef.current = {};
      setFirstVideoTime(null);
      setPipelineStartTime(Date.now());
      
      const wavBlob = float32ArrayToWav(audioData);
      
      if (wavBlob.size < 2000) {
        setStatus('Listening...');
        setIsProcessing(false);
        return;
      }
      
      // Step 1: Transcribe audio
      setCurrentPhase('transcribing');
      setStatus('🎤 Transcribing...');
      
      const transcribeFormData = new FormData();
      transcribeFormData.append('audio', new File([wavBlob], 'speech.wav', { type: 'audio/wav' }));
      
      const transcribeResponse = await fetch(`${API_BASE_URL}/transcribe`, {
        method: 'POST',
        body: transcribeFormData
      });
      
      const transcribeData = await transcribeResponse.json();
      const userQuestion = transcribeData.text || '';
      setCurrentUserText(userQuestion);
      
      console.log('📝 User said:', userQuestion);
      
      // Step 2: Start parallel pipeline
      setCurrentPhase('pipeline_started');
      setStatus('⚡ Processing with parallel pipeline...');
      
      const pipelineRequest = {
        question: userQuestion,
        reference_audio: referenceVoiceId ? `audio/reference_voices/${referenceVoiceId}.wav` : undefined,
        reference_image: referencePictureId ? `Avatar/References/${referencePictureId}.jpg` : undefined,
        emotion: 4,
        pose: {},
        gaze: true
      };
      
      abortControllerRef.current = new AbortController();
      
      const response = await fetch(`${API_BASE_URL}/api/parallel-pipeline/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(pipelineRequest),
        signal: abortControllerRef.current.signal
      });
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              handlePipelineEvent(data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('🛑 Pipeline aborted');
      } else {
        console.error('❌ Error:', error);
        setError(error.message);
        setStatus('Error');
      }
    } finally {
      setIsProcessing(false);
      if (isListening && !isAISpeaking) {
        setStatus('Listening...');
      }
    }
  };
  
  // Handle pipeline events
  const handlePipelineEvent = (data) => {
    console.log('📦 Pipeline event:', data.event, data);
    
    switch (data.event) {
      case 'started':
        setSessionId(data.session_id);
        setStatus('⚡ Pipeline running...');
        setCurrentPhase('pipeline_running');
        pipelineMetricsRef.current.started = Date.now();
        break;
      
      case 'video_chunk':
        const elapsed = Date.now() - pipelineStartTime;
        
        if (firstVideoTime === null) {
          setFirstVideoTime(elapsed / 1000);
          console.log(`🎉 First video in ${(elapsed / 1000).toFixed(2)}s`);
        }
        
        // Add video to queue
        videoQueueRef.current.push({
          url: `${API_BASE_URL}${data.video_url}`,
          duration: data.duration,
          text: data.text,
          chunkIdx: data.chunk_idx
        });
        
        setVideoProgress(prev => ({
          current: prev.current + 1,
          total: prev.total + 1
        }));
        
        setCurrentAIText(prev => prev + ' ' + data.text);
        setCurrentPhase('playing_video');
        setStatus(`📹 Playing video ${data.chunk_idx + 1}...`);
        
        // Start playing if not already playing
        if (!isPlayingVideoRef.current) {
          playVideoQueue();
        }
        break;
      
      case 'complete':
        console.log(`✅ Pipeline complete: ${data.total_videos} videos in ${data.total_time}s`);
        pipelineMetricsRef.current.complete = Date.now();
        pipelineMetricsRef.current.totalVideos = data.total_videos;
        pipelineMetricsRef.current.totalTime = data.total_time;
        setCurrentPhase('complete');
        break;
      
      case 'error':
        console.error('❌ Pipeline error:', data.message);
        setError(data.message);
        setStatus('Error');
        setCurrentPhase('error');
        break;
      
      default:
        console.log('Unknown event:', data.event);
    }
  };
  
  // Play video queue
  const playVideoQueue = async () => {
    if (isPlayingVideoRef.current || videoQueueRef.current.length === 0) {
      return;
    }
    
    isPlayingVideoRef.current = true;
    setIsAISpeaking(true);
    
    while (videoQueueRef.current.length > 0) {
      const videoChunk = videoQueueRef.current.shift();
      
      await playVideoChunk(videoChunk);
    }
    
    isPlayingVideoRef.current = false;
    setIsAISpeaking(false);
    
    setStatus(isListening ? 'Listening...' : 'Ready to start conversation');
  };
  
  // Play single video chunk
  const playVideoChunk = (chunk) => {
    return new Promise((resolve) => {
      if (!avatarVideoRef.current) {
        resolve();
        return;
      }
      
      avatarVideoRef.current.src = chunk.url;
      avatarVideoRef.current.onended = () => {
        resolve();
      };
      avatarVideoRef.current.onerror = () => {
        console.error('Video playback error');
        resolve();
      };
      avatarVideoRef.current.play().catch(err => {
        console.error('Failed to play video:', err);
        resolve();
      });
    });
  };
  
  // Toggle listening
  const toggleListening = async () => {
    if (isListening) {
      vad.pause();
      setStatus('Stopped');
      
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    } else {
      setError(null);
      try {
        await vad.start();
        setStatus('Listening...');
      } catch (err) {
        console.error('❌ Failed to start:', err);
        setError('Failed to start: ' + err.message);
      }
    }
  };
  
  return (
    <div className="voice-agent-container">
      <div className="main-content">
        <div className="avatar-section">
          <div className="avatar-window">
            <video
              ref={avatarVideoRef}
              className="avatar-video"
              playsInline
              muted={false}
            />
            {!isAISpeaking && (
              <div className="avatar-placeholder">
                <div className="avatar-icon">🤖</div>
                <div className="avatar-text">
                  {isProcessing ? 'Processing...' : 'Waiting to speak...'}
                </div>
              </div>
            )}
          </div>
          
          {/* Metrics Display */}
          {firstVideoTime && (
            <div className="metrics-display">
              <div className="metric">
                <span className="metric-label">First Video:</span>
                <span className="metric-value">{firstVideoTime.toFixed(2)}s</span>
                {firstVideoTime < 5 && <span className="metric-badge">🎯 Target!</span>}
                {firstVideoTime >= 5 && firstVideoTime < 10 && <span className="metric-badge">⚡ Fast</span>}
              </div>
              <div className="metric">
                <span className="metric-label">Videos:</span>
                <span className="metric-value">{videoProgress.total}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Session:</span>
                <span className="metric-value">{sessionId}</span>
              </div>
            </div>
          )}
        </div>
        
        <div className="conversation-section">
          <div className="status-bar">
            <div className="status-indicator">
              <span className={`status-dot ${isListening ? 'listening' : ''} ${isProcessing ? 'processing' : ''}`}></span>
              <span className="status-text">{status}</span>
            </div>
            {firstVideoTime && (
              <div className="performance-badge">
                ⚡ Parallel Pipeline
              </div>
            )}
          </div>
          
          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}
          
          <div className="conversation-display">
            {currentUserText && (
              <div className="message user-message">
                <div className="message-label">You:</div>
                <div className="message-text">{currentUserText}</div>
              </div>
            )}
            
            {currentAIText && (
              <div className="message ai-message">
                <div className="message-label">AI:</div>
                <div className="message-text">{currentAIText}</div>
              </div>
            )}
            
            {currentPhase && (
              <div className="phase-indicator">
                Phase: <strong>{currentPhase.replace(/_/g, ' ')}</strong>
              </div>
            )}
          </div>
          
          <div className="controls">
            <button
              className={`control-button ${isListening ? 'active' : ''}`}
              onClick={toggleListening}
              disabled={!isReady || isProcessing}
            >
              {isListening ? '🛑 Stop' : '🎤 Start'}
            </button>
            
            {isProcessing && (
              <div className="processing-indicator">
                <div className="spinner"></div>
                <span>Processing...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParallelPipelineAgent;

