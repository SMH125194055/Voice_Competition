import React, { useState, useRef, useEffect } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';
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
  const [conversationHistory, setConversationHistory] = useState([]);
  
  // Current conversation states
  const [currentUserText, setCurrentUserText] = useState('');
  const [currentAIText, setCurrentAIText] = useState('');
  const [streamingUserWords, setStreamingUserWords] = useState([]);
  const [streamingAIWords, setStreamingAIWords] = useState([]);
  const [currentWordIndex, setCurrentWordIndex] = useState(-1);
  const [currentPhase, setCurrentPhase] = useState('');
  const [chunkProgress, setChunkProgress] = useState({ current: 0, total: 0 });
  
  // Refs
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const abortControllerRef = useRef(null);
  const currentAudioRef = useRef(null);
  
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
      setStatus('Listening to you...');
    },
    onSpeechEnd: (audio) => {
      console.log('🔇 Speech ended, processing...');
      setIsSpeaking(false);
      setStatus('Processing...');
      processAudioDataStreaming(audio);
    },
    onVADMisfire: () => {
      console.log('❌ VAD misfire');
      setIsSpeaking(false);
      setStatus('Listening...');
    },
    positiveSpeechThreshold: 0.6,
    negativeSpeechThreshold: 0.5,
    minSpeechFrames: 5,
    redemptionFrames: 8,
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
      console.error('❌ VAD Error:', vad.errored);
    } else {
      setStatus('Ready! Click Start to begin');
      setIsReady(true);
      console.log('✅ VAD ready');
    }
  }, [vad.loading, vad.errored]);
  
  // Update listening state
  useEffect(() => {
    setIsListening(vad.listening);
    if (vad.listening && !isProcessing && !isAISpeaking) {
      setStatus('Listening...');
    }
  }, [vad.listening, isProcessing, isAISpeaking]);
  
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
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);
    
    const offset = 44;
    for (let i = 0; i < numFrames; i++) {
      const sample = Math.max(-1, Math.min(1, audioData[i]));
      view.setInt16(offset + i * 2, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
    }
    
    return new Blob([buffer], { type: 'audio/wav' });
  };
  
  // Stream text word by word
  const streamTextWords = async (text, setWordsCallback, delayMs = 80) => {
    const words = text.split(' ');
    setWordsCallback([]);
    
    for (let i = 0; i < words.length; i++) {
      await new Promise(resolve => setTimeout(resolve, delayMs));
      setWordsCallback(prev => [...prev, words[i]]);
    }
  };
  
  // Play audio chunk with word highlighting
  const playAudioChunk = async (base64Audio, chunkWords, startWordIndex) => {
    return new Promise((resolve) => {
      try {
        const audio = new Audio(`data:audio/wav;base64,${base64Audio}`);
        currentAudioRef.current = audio;
        
        audio.addEventListener('loadedmetadata', () => {
          const duration = audio.duration * 1000;
          const wordDelay = chunkWords.length > 0 ? duration / chunkWords.length : 0;
          
          // Highlight each word as it's spoken
          chunkWords.forEach((_, idx) => {
            setTimeout(() => {
              const newIndex = startWordIndex + idx;
              setCurrentWordIndex(newIndex);
              
              // Auto-scroll to highlighted word in AI text box
              setTimeout(() => {
                const highlightedWord = document.querySelector('.text-scroll-content .word.highlighted');
                if (highlightedWord) {
                  highlightedWord.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
              }, 50);
            }, wordDelay * idx);
          });
          
          // Clear highlight at end
          setTimeout(() => {
            setCurrentWordIndex(-1);
          }, duration);
        });
        
        audio.addEventListener('ended', () => {
          currentAudioRef.current = null;
          resolve();
        });
        
        audio.addEventListener('error', (e) => {
          console.error('❌ Audio error:', e);
          currentAudioRef.current = null;
          resolve();
        });
        
        audio.play();
      } catch (error) {
        console.error('❌ Failed to play:', error);
        currentAudioRef.current = null;
        resolve();
      }
    });
  };
  
  // Process audio queue
  const processAudioQueue = async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) {
      return;
    }
    
    isPlayingRef.current = true;
    setIsAISpeaking(true);
    
    let wordIndex = 0;
    
    while (audioQueueRef.current.length > 0) {
      const chunk = audioQueueRef.current.shift();
      
      // Add chunk words to display
      const chunkWords = chunk.text.split(' ');
      setStreamingAIWords(prev => [...prev, ...chunkWords]);
      
      // Play audio with highlighting
      await playAudioChunk(chunk.audio, chunkWords, wordIndex);
      wordIndex += chunkWords.length;
      
      // Update progress
      setChunkProgress(prev => ({ ...prev, current: prev.current + 1 }));
    }
    
    isPlayingRef.current = false;
    setIsAISpeaking(false);
    setCurrentWordIndex(-1);
    
    // Save to history - ALWAYS save when both texts exist
    if (currentUserText && currentAIText) {
      const newConversation = {
        user: currentUserText,
        ai: currentAIText,
        timestamp: new Date()
      };
      
      console.log('💾 Saving to history:', newConversation);
      
      setConversationHistory(prev => {
        const updated = [...prev, newConversation];
        console.log('📚 History now has:', updated.length, 'conversations');
        return updated;
      });
      
      // Clear current conversation
      setCurrentUserText('');
      setCurrentAIText('');
      setStreamingUserWords([]);
      setStreamingAIWords([]);
    }
    
    setStatus(isListening ? 'Listening...' : 'Ready');
    setChunkProgress({ current: 0, total: 0 });
  };
  
  // Stop user speaking
  const stopUserSpeaking = () => {
    console.log('🛑 Stopping user speech...');
    if (isSpeaking) {
      vad.pause();
      setIsSpeaking(false);
      setStatus('Stopped by user');
      
      // If we have partial user text, keep it
      if (streamingUserWords.length > 0) {
        setCurrentUserText(streamingUserWords.join(' '));
      }
    }
  };
  
  // Stop AI speaking
  const stopAISpeaking = () => {
    console.log('🛑 Stopping AI speech...');
    
    // Stop current audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    
    // Clear queue
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setIsAISpeaking(false);
    setCurrentWordIndex(-1);
    setChunkProgress({ current: 0, total: 0 });
    
    // Save partial conversation to history if we have both texts
    if (currentUserText && (currentAIText || streamingAIWords.length > 0)) {
      const aiText = currentAIText || streamingAIWords.join(' ');
      const partialConv = {
        user: currentUserText,
        ai: aiText,
        timestamp: new Date()
      };
      
      console.log('💾 Saving partial to history:', partialConv);
      
      setConversationHistory(prev => {
        const updated = [...prev, partialConv];
        console.log('📚 History now has:', updated.length, 'conversations');
        return updated;
      });
      
      // Clear current
      setCurrentUserText('');
      setCurrentAIText('');
      setStreamingUserWords([]);
      setStreamingAIWords([]);
    }
    
    setStatus(isListening ? 'Listening...' : 'Ready');
  };
  
  // Process audio with SSE streaming
  const processAudioDataStreaming = async (audioData) => {
    if (isProcessing || isAISpeaking) {
      console.log('⏭️ Busy, skipping');
      return;
    }
    
    try {
      setIsProcessing(true);
      setError(null);
      setCurrentUserText('');
      setCurrentAIText('');
      setStreamingUserWords([]);
      setStreamingAIWords([]);
      setCurrentWordIndex(-1);
      setCurrentPhase('');
      setChunkProgress({ current: 0, total: 0 });
      audioQueueRef.current = [];
      
      console.log('📡 Starting SSE stream...');
      
      const wavBlob = float32ArrayToWav(audioData);
      console.log('📦 Audio size:', wavBlob.size);
      
      if (wavBlob.size < 2000) {
        console.log('⚠️ Audio too short');
        setStatus('Listening...');
        setIsProcessing(false);
        return;
      }
      
      const formData = new FormData();
      formData.append('audio', new File([wavBlob], 'speech.wav', { type: 'audio/wav' }));
      
      abortControllerRef.current = new AbortController();
      
      const response = await fetch(`${API_BASE_URL}/vad-chat-voice-stream`, {
        method: 'POST',
        body: formData,
        signal: abortControllerRef.current.signal
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      let userTextReceived = '';
      let aiTextReceived = '';
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          console.log('✅ Stream complete');
          break;
        }
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('event:')) continue;
          
          if (line.startsWith('data:')) {
            const data = JSON.parse(line.substring(6).trim());
            
            // VAD complete
            if (data.has_speech !== undefined) {
              setCurrentPhase('vad');
              setStatus(`✅ Speech detected (${data.duration}s)`);
            }
            
            // User transcription
            if (data.text && !userTextReceived && !data.audio) {
              setCurrentPhase('transcription');
              userTextReceived = data.text;
              setCurrentUserText(data.text);
              setStatus('📝 You said...');
              
              // Stream user text word by word
              await streamTextWords(data.text, setStreamingUserWords, 60);
              console.log('💬 User:', data.text);
            }
            
            // AI response
            if (data.text && userTextReceived && !aiTextReceived && !data.audio) {
                  setCurrentPhase('llm');
              aiTextReceived = data.text;
              setCurrentAIText(data.text);
              setStatus('🤖 AI responding...');
              console.log('🤖 AI:', data.text);
            }
            
            // TTS chunks
            if (data.audio) {
                  setCurrentPhase('tts');
              setChunkProgress({ current: data.chunk_index, total: data.total_chunks });
              setStatus(`🔊 Speaking (${data.chunk_index + 1}/${data.total_chunks})...`);
              
              audioQueueRef.current.push({
                audio: data.audio,
                text: data.text,
                words: data.words
              });
              
              if (!isPlayingRef.current) {
                processAudioQueue();
              }
            }
            
            // Complete
            if (data.message === 'Conversation complete') {
              console.log('🎉 Complete!');
              setCurrentPhase('complete');
            }
            
            // Errors
            if (data.error) {
              console.error('❌ Server error:', data.error);
              setError(data.error);
              setStatus('Error occurred');
            }
          }
        }
      }
      
    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('🛑 Aborted');
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
  
  // Toggle listening
  const toggleListening = async () => {
    if (isListening) {
      console.log('🛑 Stopping...');
      vad.pause();
      setStatus('Stopped');
      
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      
      stopAISpeaking();
    } else {
      console.log('▶️ Starting...');
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
    <div className="vad-voice-agent">
      {/* Header */}
      <div className="vad-header">
        <div className="vad-title">
          <span className="vad-icon">🎙️</span>
          <h1>Voice Agent with Streaming & Cloning</h1>
        </div>
        <div className="vad-status-badge">
          {isReady ? '✓ Ready' : vad.loading ? '⏳ Loading...' : '⚠️ Error'}
        </div>
      </div>
      
      {/* Main Voice Circles Area */}
      <div className="voice-circles-container">
        {/* Human Circle (Left) */}
        <div className={`voice-circle human-circle ${isSpeaking ? 'active' : ''}`}>
          <div className="circle-content">
            <div className="circle-avatar">👤</div>
            <div className="circle-label">You</div>
            {isSpeaking && (
              <>
                <button className="stop-circle-btn" onClick={stopUserSpeaking} title="Stop speaking">
                  🛑
                </button>
                <div className="pulse-ring"></div>
                <div className="pulse-ring delay-1"></div>
                <div className="pulse-ring delay-2"></div>
              </>
            )}
          </div>
          
          {/* User Text Below Circle - FIXED HEIGHT WITH SCROLL */}
          {streamingUserWords.length > 0 && (
            <div className="circle-text-box user-text-box">
              <div className="text-scroll-content">
                {streamingUserWords.map((word, idx) => (
                  <span key={idx} className="word appear">
                    {word}{' '}
                  </span>
                ))}
          </div>
            </div>
          )}
        </div>
        
        {/* Central Control */}
        <div className="central-control">
          <button
            className={`control-button ${isListening ? 'listening' : ''}`}
            onClick={toggleListening}
            disabled={!isReady || isProcessing}
          >
            <span className="button-icon">
              {isListening ? '⏹️' : '▶️'}
            </span>
            <span className="button-text">
              {isListening ? 'Stop' : 'Start'}
            </span>
          </button>
          
          <div className="status-info">
            <div className="status-message">{status}</div>
            
            {currentPhase && (
              <div className="phase-dots">
                <span className={`dot ${currentPhase === 'vad' ? 'active' : currentPhase !== 'vad' && currentPhase !== '' ? 'done' : ''}`} title="VAD"></span>
                <span className={`dot ${currentPhase === 'transcription' ? 'active' : ['llm', 'tts', 'complete'].includes(currentPhase) ? 'done' : ''}`} title="STT"></span>
                <span className={`dot ${currentPhase === 'llm' ? 'active' : ['tts', 'complete'].includes(currentPhase) ? 'done' : ''}`} title="LLM"></span>
                <span className={`dot ${['tts', 'complete'].includes(currentPhase) ? 'active' : ''}`} title="TTS"></span>
              </div>
            )}
            
            {chunkProgress.total > 0 && (
              <div className="chunk-progress">
                <div className="progress-bar-mini">
                  <div 
                    className="progress-fill-mini" 
                    style={{ width: `${(chunkProgress.current / chunkProgress.total) * 100}%` }}
                  ></div>
                </div>
                <span className="progress-label">
                  {chunkProgress.current}/{chunkProgress.total}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* AI Circle (Right) */}
        <div className={`voice-circle ai-circle ${isAISpeaking ? 'active' : ''}`}>
          <div className="circle-content">
            <div className="circle-avatar">🤖</div>
            <div className="circle-label">AI Assistant</div>
            {isAISpeaking && (
              <>
                <button className="stop-circle-btn" onClick={stopAISpeaking} title="Stop AI speaking">
                  🛑
                </button>
                <div className="pulse-ring"></div>
                <div className="pulse-ring delay-1"></div>
                <div className="pulse-ring delay-2"></div>
              </>
            )}
          </div>
          
          {/* AI Text Below Circle - FIXED HEIGHT WITH SCROLL AND HIGHLIGHTING */}
          {streamingAIWords.length > 0 && (
            <div className="circle-text-box ai-text-box">
              <div className="text-scroll-content">
                {streamingAIWords.map((word, idx) => (
                  <span 
                    key={idx} 
                    className={`word appear ${idx === currentWordIndex ? 'highlighted' : idx < currentWordIndex ? 'spoken' : ''}`}
                  >
                    {word}{' '}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span className="error-icon">⚠️</span>
          <span className="error-text">{error}</span>
          <button className="error-close" onClick={() => setError(null)}>×</button>
        </div>
      )}
      
      {/* Conversation History */}
      <div className="conversation-history">
        <div className="history-header">
          <h2>💬 Conversation History</h2>
          {conversationHistory.length > 0 && (
            <button className="clear-btn" onClick={() => setConversationHistory([])}>
              🗑️ Clear
            </button>
          )}
        </div>

        <div className="history-messages">
          {conversationHistory.length === 0 && streamingUserWords.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">🎙️</div>
              <div className="empty-title">Ready for Conversation</div>
              <div className="empty-subtitle">
                Click "Start" and speak naturally
              </div>
              <div className="feature-tags">
                <span className="tag">🎭 Voice Cloning</span>
                <span className="tag">⚡ Streaming</span>
                <span className="tag">✨ Highlighting</span>
              </div>
            </div>
          ) : (
            <>
              {conversationHistory.map((conv, idx) => (
                <div key={idx} className="conversation-pair">
                  {/* User Message (Left) */}
                  <div className="message-row left">
                    <div className="message-bubble user-bubble">
                      <div className="message-avatar">👤</div>
                      <div className="message-content">
                        <div className="message-header">
                          <span className="message-author">You</span>
                          <span className="message-time">
                            {conv.timestamp.toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="message-text">{conv.user}</div>
                      </div>
                    </div>
                  </div>

                  {/* AI Message (Right) */}
                  <div className="message-row right">
                    <div className="message-bubble ai-bubble">
                      <div className="message-content">
                        <div className="message-header">
                          <span className="message-author">AI Assistant</span>
                          <span className="message-time">
                            {conv.timestamp.toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="message-text">{conv.ai}</div>
                      </div>
                      <div className="message-avatar">🤖</div>
                </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
      
      {/* Features Footer */}
      <div className="features-footer">
        <div className="feature-item">
          <span className="feature-icon">🎭</span>
          <span className="feature-label">Clones Your Voice</span>
        </div>
        <div className="feature-item">
          <span className="feature-icon">⚡</span>
          <span className="feature-label">Real-time Streaming</span>
        </div>
        <div className="feature-item">
          <span className="feature-icon">✨</span>
          <span className="feature-label">Word Highlighting</span>
        </div>
        <div className="feature-item">
          <span className="feature-icon">🎯</span>
          <span className="feature-label">Smart VAD</span>
        </div>
      </div>
    </div>
  );
};

export default VADVoiceAgent;
