import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';
import './LargeVideoAgent.css';

const API_BASE_URL = 'http://localhost:8001';

const LargeVideoAgent = () => {
  // State management
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
  
  // Voice mode and settings
  const [voiceMode, setVoiceMode] = useState('inference');
  const [allowInterruption, setAllowInterruption] = useState(true);
  const [referenceVoiceId, setReferenceVoiceId] = useState(null);
  const [referenceVoices, setReferenceVoices] = useState([]);
  const [isRecordingReference, setIsRecordingReference] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  // Avatar settings
  const [enableAvatar, setEnableAvatar] = useState(true);
  const [referencePictureId, setReferencePictureId] = useState(null);
  const [referencePictures, setReferencePictures] = useState([]);
  const [avatarVideoUrl, setAvatarVideoUrl] = useState(null);
  const avatarVideoRef = useRef(null);
  
  // NEW: Advanced Generation Settings
  const [avatarSize, setAvatarSize] = useState(256);
  const [avatarFPS, setAvatarFPS] = useState(25);
  const [generationQuality, setGenerationQuality] = useState('balanced'); // fast, balanced, quality
  const [enhancer, setEnhancer] = useState('none'); // none, gfpgan
  
  // Audio player states
  const [isPlayingReference, setIsPlayingReference] = useState(false);
  const [referenceAudioProgress, setReferenceAudioProgress] = useState(0);
  const [referenceAudioDuration, setReferenceAudioDuration] = useState(0);
  
  // UI States
  const [showParticipants, setShowParticipants] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // VAD sensitivity fixed to HIGH
  const vadSensitivity = 'high';
  
  // Refs
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const abortControllerRef = useRef(null);
  const currentAudioRef = useRef(null);
  const referenceRecorderRef = useRef(null);
  const referenceAudioChunksRef = useRef([]);
  const isInterruptedRef = useRef(false);
  const referencePlayerRef = useRef(null);
  const containerRef = useRef(null);
  
  // Generation presets
  const generationPresets = {
    fast: {
      label: '⚡ Fast',
      description: 'Quick generation, lower quality',
      size: 128,
      fps: 15,
      enhancer: 'none',
      batchSize: 1,
      color: '#10b981'
    },
    balanced: {
      label: '⚖️ Balanced',
      description: 'Good balance of speed and quality',
      size: 256,
      fps: 25,
      enhancer: 'none',
      batchSize: 1,
      color: '#3b82f6'
    },
    quality: {
      label: '💎 Quality',
      description: 'Best quality, slower generation',
      size: 512,
      fps: 30,
      enhancer: 'gfpgan',
      batchSize: 2,
      color: '#8b5cf6'
    }
  };
  
  // Apply preset
  const applyPreset = (preset) => {
    const config = generationPresets[preset];
    setAvatarSize(config.size);
    setAvatarFPS(config.fps);
    setEnhancer(config.enhancer);
    setGenerationQuality(preset);
  };
  
  // VAD sensitivity configurations
  const vadConfigs = useMemo(() => ({
    low: {
      positiveSpeechThreshold: 0.5,
      negativeSpeechThreshold: 0.35,
      minSpeechFrames: 3,
      redemptionFrames: 8,
    },
    medium: {
      positiveSpeechThreshold: 0.7,
      negativeSpeechThreshold: 0.5,
      minSpeechFrames: 5,
      redemptionFrames: 8,
    },
    high: {
      positiveSpeechThreshold: 0.85,
      negativeSpeechThreshold: 0.65,
      minSpeechFrames: 8,
      redemptionFrames: 10,
    },
  }), []);
  
  const currentVadConfig = vadConfigs[vadSensitivity];
  
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
      
      if ((isAISpeaking || isProcessing) && allowInterruption) {
        console.log('🛑 Interruption detected!');
        stopAISpeaking();
      }
      
      setStatus('Listening to you...');
    },
    onSpeechEnd: (audio) => {
      console.log('🔇 Speech ended');
      setStatus('Processing...');
      processAudioDataStreaming(audio);
    },
    onVADMisfire: () => {
      console.log('❌ VAD misfire');
      setStatus('Listening...');
    },
    positiveSpeechThreshold: currentVadConfig.positiveSpeechThreshold,
    negativeSpeechThreshold: currentVadConfig.negativeSpeechThreshold,
    minSpeechFrames: currentVadConfig.minSpeechFrames,
    redemptionFrames: currentVadConfig.redemptionFrames,
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
  
  // Play audio chunk with avatar video
  const playAudioChunk = async (base64Audio, chunkWords, startWordIndex, avatarVideoBase64 = null, hasAvatar = false) => {
    return new Promise((resolve) => {
      try {
        if (hasAvatar && avatarVideoBase64) {
          console.log('🎬 Playing avatar video chunk...');
          
          try {
            const byteCharacters = atob(avatarVideoBase64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
              byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'video/mp4' });
            const videoUrl = URL.createObjectURL(blob);
            
            setAvatarVideoUrl(videoUrl);
            
            setTimeout(() => {
              if (avatarVideoRef.current) {
                const video = avatarVideoRef.current;
                video.muted = false; // Unmute so we hear the video's audio
                video.src = videoUrl;
                video.load();
                
                currentAudioRef.current = video;
                
                video.addEventListener('loadedmetadata', () => {
                  const duration = video.duration * 1000;
                  const wordDelay = chunkWords.length > 0 ? duration / chunkWords.length : 0;
                  
                  chunkWords.forEach((_, idx) => {
                    setTimeout(() => {
                      setCurrentWordIndex(startWordIndex + idx);
                    }, wordDelay * idx);
                  });
                  
                  setTimeout(() => {
                    setCurrentWordIndex(-1);
                  }, duration);
                }, { once: true });
                
                video.addEventListener('ended', () => {
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);
                  resolve();
                }, { once: true });
                
                video.addEventListener('error', (e) => {
                  console.error('❌ Video error:', e);
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);
                  // Only play audio fallback on video error
                  playAudioOnly();
                });
                
                // Play the video (which has audio embedded)
                video.play().catch(err => {
                  console.error('❌ Failed to play video:', err);
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);
                  // If video play fails, use audio fallback
                  playAudioOnly();
                });
              } else {
                playAudioOnly();
              }
            }, 100);
          } catch (error) {
            console.error('❌ Error creating video:', error);
            playAudioOnly();
          }
        } else {
          playAudioOnly();
        }
        
        function playAudioOnly() {
          const audio = new Audio(`data:audio/wav;base64,${base64Audio}`);
          currentAudioRef.current = audio;
          
          audio.addEventListener('loadedmetadata', () => {
            const duration = audio.duration * 1000;
            const wordDelay = chunkWords.length > 0 ? duration / chunkWords.length : 0;
            
            chunkWords.forEach((_, idx) => {
              setTimeout(() => {
                setCurrentWordIndex(startWordIndex + idx);
              }, wordDelay * idx);
            });
            
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
        }
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
      
      const chunkWords = chunk.text.split(' ');
      setStreamingAIWords(prev => [...prev, ...chunkWords]);
      
      await playAudioChunk(chunk.audio, chunkWords, wordIndex, chunk.avatarVideo, chunk.hasAvatar);
      wordIndex += chunkWords.length;
      
      setChunkProgress(prev => ({ ...prev, current: prev.current + 1 }));
    }
    
    isPlayingRef.current = false;
    setIsAISpeaking(false);
    setCurrentWordIndex(-1);
    
    if (currentUserText && currentAIText) {
      const newConversation = {
        user: currentUserText,
        ai: currentAIText,
        timestamp: new Date()
      };
      
      setConversationHistory(prev => [...prev, newConversation]);
      
      setCurrentUserText('');
      setCurrentAIText('');
      setStreamingUserWords([]);
      setStreamingAIWords([]);
    }
    
    setStatus(isListening ? 'Listening...' : 'Ready to start conversation');
    setChunkProgress({ current: 0, total: 0 });
  };
  
  // Stop AI speaking
  const stopAISpeaking = () => {
    console.log('🛑 Stopping AI...');
    
    isInterruptedRef.current = true;
    
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    
    if (avatarVideoRef.current) {
      avatarVideoRef.current.pause();
      avatarVideoRef.current.currentTime = 0;
    }
    
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setIsAISpeaking(false);
    setIsProcessing(false);
    setCurrentWordIndex(-1);
    setChunkProgress({ current: 0, total: 0 });
    setCurrentPhase('');
    
    if (currentUserText && currentAIText) {
      const partialConv = {
        user: currentUserText,
        ai: currentAIText,
        timestamp: new Date()
      };
      
      setConversationHistory(prev => [...prev, partialConv]);
      
      setCurrentUserText('');
      setCurrentAIText('');
      setStreamingUserWords([]);
      setStreamingAIWords([]);
    }
    
    setStatus(isListening ? 'Listening...' : 'Ready to start conversation');
  };
  
  // Load reference voices and pictures
  useEffect(() => {
    const loadResources = async () => {
      await loadReferenceVoices();
      await loadReferencePictures();
    };
    loadResources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  
  const loadReferenceVoices = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/list-reference-voices`);
      const data = await response.json();
      setReferenceVoices(data.voices || []);
      
      if (voiceMode === 'inference' && !referenceVoiceId && data.voices.length > 0) {
        setReferenceVoiceId(data.voices[0].id);
      }
    } catch (error) {
      console.error('Failed to load reference voices:', error);
    }
  };
  
  const startReferenceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      referenceRecorderRef.current = mediaRecorder;
      referenceAudioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          referenceAudioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(referenceAudioChunksRef.current, { type: 'audio/webm' });
        await uploadReferenceVoice(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      setIsRecordingReference(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('Failed to access microphone.');
    }
  };
  
  const stopReferenceRecording = () => {
    if (referenceRecorderRef.current && referenceRecorderRef.current.state !== 'inactive') {
      referenceRecorderRef.current.stop();
      setIsRecordingReference(false);
    }
  };
  
  const uploadReferenceVoice = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'reference.webm');
      
      const response = await fetch(`${API_BASE_URL}/upload-reference-voice`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadReferenceVoices();
        setReferenceVoiceId(data.reference_voice_id);
        alert(`Reference voice saved! Duration: ${data.duration}s`);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Failed to upload reference voice:', error);
      alert('Failed to upload reference voice.');
    }
  };
  
  // eslint-disable-next-line no-unused-vars
  const deleteReferenceVoice = async (voiceId) => {
    if (!window.confirm('Delete this reference voice?')) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/delete-reference-voice/${voiceId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadReferenceVoices();
        if (referenceVoiceId === voiceId) {
          setReferenceVoiceId(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete reference voice:', error);
      alert('Failed to delete reference voice.');
    }
  };
  
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    await uploadReferenceVoice(file);
    event.target.value = '';
  };
  
  const initializeReferencePlayer = () => {
    if (!referenceVoiceId || !referencePlayerRef.current) return;
    
    const voice = referenceVoices.find(v => v.id === referenceVoiceId);
    if (!voice) return;
    
    const audioUrl = `${API_BASE_URL}/audio/reference_voices/${voice.filename}?t=${Date.now()}`;
    
    setIsPlayingReference(false);
    setReferenceAudioProgress(0);
    setReferenceAudioDuration(0);
    
    referencePlayerRef.current.src = audioUrl;
    referencePlayerRef.current.load();
    
    referencePlayerRef.current.onloadedmetadata = () => {
      setReferenceAudioDuration(referencePlayerRef.current.duration);
    };
    
    referencePlayerRef.current.ontimeupdate = () => {
      setReferenceAudioProgress(referencePlayerRef.current.currentTime);
    };
    
    referencePlayerRef.current.onended = () => {
      setIsPlayingReference(false);
      setReferenceAudioProgress(0);
    };
    
    referencePlayerRef.current.onplay = () => {
      setIsPlayingReference(true);
    };
    
    referencePlayerRef.current.onpause = () => {
      setIsPlayingReference(false);
    };
  };
  
  const togglePlayReferenceVoice = () => {
    if (!referencePlayerRef.current) return;
    
    if (isPlayingReference) {
      referencePlayerRef.current.pause();
    } else {
      if (referencePlayerRef.current.ended || referencePlayerRef.current.error) {
        initializeReferencePlayer();
        setTimeout(() => {
          if (referencePlayerRef.current) {
            referencePlayerRef.current.play().catch(err => console.error('Play error:', err));
          }
        }, 200);
      } else {
        referencePlayerRef.current.play().catch(err => console.error('Play error:', err));
      }
    }
  };
  
  const seekReferenceAudio = (time) => {
    if (!referencePlayerRef.current) return;
    referencePlayerRef.current.currentTime = time;
    setReferenceAudioProgress(time);
  };
  
  const stopReferenceAudio = () => {
    if (!referencePlayerRef.current) return;
    referencePlayerRef.current.pause();
    referencePlayerRef.current.currentTime = 0;
    setIsPlayingReference(false);
    setReferenceAudioProgress(0);
  };
  
  useEffect(() => {
    if (referenceVoiceId && referencePlayerRef.current) {
      initializeReferencePlayer();
    }
  }, [referenceVoiceId, referenceVoices]);
  
  const loadReferencePictures = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/list-reference-pictures`);
      const data = await response.json();
      setReferencePictures(data.pictures || []);
      
      if (enableAvatar && !referencePictureId && data.pictures.length > 0) {
        setReferencePictureId(data.pictures[0].id);
      }
    } catch (error) {
      console.error('Failed to load reference pictures:', error);
    }
  };
  
  const handlePictureUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
      const formData = new FormData();
      formData.append('image', file);
      
      const response = await fetch(`${API_BASE_URL}/upload-reference-picture`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadReferencePictures();
        setReferencePictureId(data.reference_picture_id);
        alert('Reference picture uploaded successfully!');
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Failed to upload reference picture:', error);
      alert('Failed to upload reference picture.');
    }
  };
  
  const deleteReferencePicture = async (pictureId) => {
    if (!window.confirm('Delete this reference picture?')) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/delete-reference-picture/${pictureId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        await loadReferencePictures();
        if (referencePictureId === pictureId) {
          setReferencePictureId(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete reference picture:', error);
      alert('Failed to delete reference picture.');
    }
  };
  
  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => {
        setIsFullscreen(true);
      }).catch(err => {
        console.error('Fullscreen error:', err);
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      });
    }
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (referencePlayerRef.current) {
        referencePlayerRef.current.pause();
        referencePlayerRef.current.src = '';
      }
      
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      
      if (referenceRecorderRef.current && referenceRecorderRef.current.state !== 'inactive') {
        referenceRecorderRef.current.stop();
      }
      
      audioQueueRef.current = [];
      isPlayingRef.current = false;
    };
  }, []);
  
  // Process audio with SSE streaming
  const processAudioDataStreaming = async (audioData) => {
    // Check BOTH state AND ref to prevent race conditions
    if (isProcessing || isAISpeaking || isPlayingRef.current) {
      console.log('🚫 Already processing, ignoring new speech');
      return;
    }
    
    try {
      isInterruptedRef.current = false;
      
      // Set processing flag immediately to prevent race conditions
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
      
      const wavBlob = float32ArrayToWav(audioData);
      
      if (wavBlob.size < 2000) {
        setStatus('Listening...');
        setIsProcessing(false);
        return;
      }
      
      const formData = new FormData();
      formData.append('audio', new File([wavBlob], 'speech.wav', { type: 'audio/wav' }));
      formData.append('voice_mode', voiceMode);
      formData.append('allow_interruption', allowInterruption.toString());
      
      if (voiceMode === 'inference' && referenceVoiceId) {
        formData.append('reference_voice_id', referenceVoiceId);
      }
      
      formData.append('enable_avatar', enableAvatar.toString());
      if (enableAvatar && referencePictureId) {
        formData.append('reference_picture_id', referencePictureId);
      }
      
      // NEW: Send generation settings
      formData.append('avatar_size', avatarSize.toString());
      formData.append('avatar_fps', avatarFPS.toString());
      formData.append('enhancer', enhancer);
      
      abortControllerRef.current = new AbortController();
      
      const endpoint = enableAvatar ? '/vad-chat-avatar-stream' : '/vad-chat-voice-stream';
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
        signal: abortControllerRef.current.signal
      });
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      let userTextReceived = '';
      let aiTextReceived = '';
      
      while (true) {
        // Check for interruption at the start of each loop iteration
        if (isInterruptedRef.current) {
          console.log('🛑 Stream interrupted, closing reader');
          reader.cancel();
          break;
        }
        
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        let currentEvent = '';
        
        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.substring(6).trim();
            continue;
          }
          
          if (line.startsWith('data:')) {
            const data = JSON.parse(line.substring(6).trim());
            
            if (data.has_speech !== undefined) {
              setCurrentPhase('vad');
              setStatus(`✅ Speech detected (${data.duration}s)`);
            }
            
            if (currentEvent === 'transcription_complete' && data.text) {
              setCurrentPhase('transcription');
              userTextReceived = data.text;
              setCurrentUserText(data.text);
              setStatus('📝 You said...');
              
              const words = data.text.split(' ');
              setStreamingUserWords(words);
            }
            
            if (currentEvent === 'llm_complete' && data.text) {
              setCurrentPhase('llm');
              aiTextReceived = data.text;
              setCurrentAIText(data.text);
              setStatus('🤖 AI responding...');
            }
            
            if (data.audio) {
              if (isInterruptedRef.current) {
                console.log('🛑 Audio chunk received but interrupted, skipping');
                reader.cancel();
                return;
              }
              
              setCurrentPhase('tts');
              setChunkProgress({ current: data.chunk_index, total: data.total_chunks });
              
              if (data.has_avatar && data.avatar_video) {
                setStatus(`🎬 Avatar speaking (${data.chunk_index + 1})...`);
              } else {
                setStatus(`🔊 Speaking (${data.chunk_index + 1})...`);
              }
              
              audioQueueRef.current.push({
                audio: data.audio,
                text: data.text,
                words: data.words,
                avatarVideo: data.avatar_video || null,
                hasAvatar: data.has_avatar || false
              });
              
              if (!isPlayingRef.current) {
                processAudioQueue();
              }
            }
            
            if (data.message === 'Conversation complete') {
              setCurrentPhase('complete');
            }
            
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
      vad.pause();
      setStatus('Stopped');
      
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      
      stopAISpeaking();
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
    <div className="video-conference-container" ref={containerRef}>
      {/* Professional Header */}
      <div className="conference-header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-icon">🎬</span>
            <span className="logo-text">AI Interview</span>
          </div>
          <div className="meeting-info">
            <span className="meeting-id">Meeting ID: {Date.now().toString().slice(-6)}</span>
            <span className="meeting-status">
              {isListening ? '🔴 Live' : '⚪ Ready'}
            </span>
          </div>
        </div>
        
        <div className="header-center">
          <div className="status-indicator">
            <div className={`status-dot ${isListening ? 'active' : ''}`}></div>
            <span className="status-text">{status}</span>
          </div>
        </div>
        
        <div className="header-right">
          <button 
            className="header-btn"
            onClick={() => setShowSettings(!showSettings)}
            title="Settings"
          >
            <span className="btn-icon">⚙️</span>
          </button>
          <button 
            className="header-btn"
            onClick={toggleFullscreen}
            title="Fullscreen"
          >
            <span className="btn-icon">{isFullscreen ? '⛶' : '⛶'}</span>
          </button>
          <button 
            className="header-btn danger"
            onClick={toggleListening}
            disabled={!isReady || isProcessing}
            title={isListening ? 'End Meeting' : 'Start Meeting'}
          >
            <span className="btn-icon">{isListening ? '📞' : '📞'}</span>
          </button>
        </div>
      </div>
      
      {/* Main Video Area */}
      <div className="main-video-area">
        {/* Large Video */}
        <div className="primary-video">
          {enableAvatar && avatarVideoUrl ? (
            <>
              <video 
                ref={avatarVideoRef}
                playsInline
                className="main-video"
                onLoadedData={() => console.log('🎬 Video loaded')}
                onError={(e) => console.error('❌ Video error:', e)}
              />
              
              {/* Video participant name tag */}
              <div className="video-nametag">
                <span className="nametag-icon">🤖</span>
                <span className="nametag-name">AI Assistant</span>
                {isAISpeaking && (
                  <span className="nametag-speaking">
                    <span className="speaking-dot"></span>
                    Speaking
                  </span>
                )}
              </div>
              
              {/* Captions/Subtitles */}
              {streamingAIWords.length > 0 && (
                <div className="video-captions">
                  <div className="captions-content">
                    {streamingAIWords.slice(-20).map((word, idx) => (
                      <span 
                        key={idx} 
                        className={`caption-word ${
                          idx === currentWordIndex - (streamingAIWords.length - 20) ? 'active' : ''
                        }`}
                      >
                        {word}{' '}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className={`video-placeholder ${
              isProcessing && currentUserText ? 'user-speaking' : 
              isAISpeaking ? 'ai-speaking' : ''
            }`}>
              <div className="placeholder-avatar">
                <div className="avatar-circle">
                  <span className="avatar-icon">🤖</span>
                </div>
                <div className="avatar-name">AI Assistant</div>
                <div className="avatar-status">
                  {isProcessing && currentUserText ? '👤 You are speaking...' :
                   isAISpeaking ? '🤖 AI is responding...' :
                   isReady ? 'Ready to connect' : 'Initializing...'}
                </div>
              </div>
            </div>
          )}
          
          {/* Controls Overlay */}
          <div className="video-controls-bar">
            <div className="controls-left">
              <button 
                className={`control-btn ${isListening ? 'active' : ''}`}
                onClick={toggleListening}
                disabled={!isReady || isProcessing}
                title={isListening ? 'Mute' : 'Unmute'}
              >
                <span className="control-icon">{isListening ? '🎤' : '🎤'}</span>
                <span className="control-label">{isListening ? 'Mute' : 'Unmute'}</span>
              </button>
              
              <button 
                className="control-btn"
                onClick={() => setEnableAvatar(!enableAvatar)}
                title={enableAvatar ? 'Stop Video' : 'Start Video'}
              >
                <span className="control-icon">📹</span>
                <span className="control-label">{enableAvatar ? 'Stop Video' : 'Start Video'}</span>
              </button>
              
              {isAISpeaking && (
                <button 
                  className="control-btn danger"
                  onClick={stopAISpeaking}
                  title="Stop AI"
                >
                  <span className="control-icon">🛑</span>
                  <span className="control-label">Stop AI</span>
                </button>
              )}
            </div>
            
            <div className="controls-center">
              <button 
                className={`main-action-btn ${isListening ? 'active' : ''}`}
                onClick={toggleListening}
                disabled={!isReady || isProcessing}
              >
                <span className="action-icon">
                  {isListening ? '⏹️' : '▶️'}
                </span>
                <span className="action-text">
                  {isListening ? 'End Meeting' : 'Start Meeting'}
                </span>
              </button>
            </div>
            
            <div className="controls-right">
              <button 
                className="control-btn"
                onClick={() => setShowParticipants(!showParticipants)}
                title="Participants"
              >
                <span className="control-icon">👥</span>
                <span className="control-label">Participants</span>
              </button>
              
              <button 
                className="control-btn"
                onClick={() => setShowSettings(!showSettings)}
                title="Settings"
              >
                <span className="control-icon">⚙️</span>
                <span className="control-label">Settings</span>
              </button>
            </div>
          </div>
        </div>
        
        {/* User Text Display (like transcription bar) */}
        {streamingUserWords.length > 0 && (
          <div className="transcription-bar">
            <div className="transcription-label">
              <span className="trans-icon">👤</span>
              <span className="trans-name">You</span>
            </div>
            <div className="transcription-text">
              {streamingUserWords.join(' ')}
            </div>
          </div>
        )}
      </div>
      
      {/* Settings Panel (Slide-in from right) */}
      {showSettings && (
        <div className="settings-panel-overlay" onClick={() => setShowSettings(false)}>
          <div className="settings-panel-content" onClick={(e) => e.stopPropagation()}>
            <div className="settings-panel-header">
              <h3>⚙️ Settings</h3>
              <button 
                className="close-btn"
                onClick={() => setShowSettings(false)}
              >
                ✕
              </button>
            </div>
            
            <div className="settings-panel-body">
              {/* Generation Quality Presets */}
              <div className="settings-section">
                <h4>🎨 Generation Quality</h4>
                <div className="preset-buttons">
                  {Object.entries(generationPresets).map(([key, preset]) => (
                    <button
                      key={key}
                      className={`preset-btn ${generationQuality === key ? 'active' : ''}`}
                      onClick={() => applyPreset(key)}
                      style={{
                        borderColor: generationQuality === key ? preset.color : undefined
                      }}
                    >
                      <div className="preset-label">{preset.label}</div>
                      <div className="preset-desc">{preset.description}</div>
                      <div className="preset-specs">
                        {preset.size}px • {preset.fps}fps
                      </div>
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Advanced Settings */}
              <div className="settings-section">
                <h4>🔧 Advanced Settings</h4>
                
                <div className="setting-item">
                  <label>
                    Avatar Size (Resolution)
                    <span className="setting-value">{avatarSize}px</span>
                  </label>
                  <input
                    type="range"
                    min="128"
                    max="512"
                    step="64"
                    value={avatarSize}
                    onChange={(e) => setAvatarSize(parseInt(e.target.value))}
                    className="slider"
                  />
                  <div className="setting-hint">
                    Higher = Better quality, slower generation
                  </div>
                </div>
                
                <div className="setting-item">
                  <label>
                    Frame Rate (FPS)
                    <span className="setting-value">{avatarFPS} fps</span>
                  </label>
                  <input
                    type="range"
                    min="15"
                    max="30"
                    step="5"
                    value={avatarFPS}
                    onChange={(e) => setAvatarFPS(parseInt(e.target.value))}
                    className="slider"
                  />
                  <div className="setting-hint">
                    Higher = Smoother video, longer processing
                  </div>
                </div>
                
                <div className="setting-item">
                  <label>Face Enhancer</label>
                  <select
                    value={enhancer}
                    onChange={(e) => setEnhancer(e.target.value)}
                    className="select-input"
                  >
                    <option value="none">None (Faster)</option>
                    <option value="gfpgan">GFPGAN (Better Quality)</option>
                  </select>
                  <div className="setting-hint">
                    GFPGAN improves face details but takes longer
                  </div>
                </div>
              </div>
              
              {/* Voice Settings */}
              <div className="settings-section">
                <h4>🎙️ Voice Settings</h4>
                
                <div className="setting-item">
                  <label>Voice Mode</label>
                  <div className="toggle-group">
                    <button
                      className={`toggle-btn ${voiceMode === 'inference' ? 'active' : ''}`}
                      onClick={() => setVoiceMode('inference')}
                    >
                      Reference Voice
                    </button>
                    <button
                      className={`toggle-btn ${voiceMode === 'real-time' ? 'active' : ''}`}
                      onClick={() => setVoiceMode('real-time')}
                    >
                      Real-time Voice
                    </button>
                  </div>
                </div>
                
                {voiceMode === 'inference' && (
                  <div className="setting-item">
                    <label>Reference Voice</label>
                    <select
                      className="select-input"
                      value={referenceVoiceId || ''}
                      onChange={(e) => setReferenceVoiceId(e.target.value)}
                    >
                      <option value="">Select voice...</option>
                      {referenceVoices.map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.id}
                        </option>
                      ))}
                    </select>
                    
                    {/* Audio Preview */}
                    {referenceVoiceId && (
                      <div className="reference-preview">
                        <audio 
                          controls 
                          src={`${API_BASE_URL}/audio/reference_voices/${referenceVoiceId}.wav?t=${Date.now()}`}
                          style={{ width: '100%', marginTop: '8px' }}
                        />
                      </div>
                    )}
                    
                    <div className="button-row">
                      <button
                        className="action-btn secondary"
                        onClick={isRecordingReference ? stopReferenceRecording : startReferenceRecording}
                      >
                        {isRecordingReference ? '⏹️ Stop' : '🎤 Record'}
                      </button>
                      <label className="action-btn secondary">
                        📁 Upload
                        <input
                          type="file"
                          accept="audio/*"
                          onChange={handleFileUpload}
                          style={{ display: 'none' }}
                        />
                      </label>
                    </div>
                  </div>
                )}
                
                <div className="setting-item">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={allowInterruption}
                      onChange={(e) => setAllowInterruption(e.target.checked)}
                    />
                    <span>Allow voice interruption</span>
                  </label>
                </div>
              </div>
              
              {/* Avatar Settings */}
              {enableAvatar && (
                <div className="settings-section">
                  <h4>🖼️ Avatar Settings</h4>
                  
                  <div className="setting-item">
                    <label>Reference Picture</label>
                    <select
                      className="select-input"
                      value={referencePictureId || ''}
                      onChange={(e) => setReferencePictureId(e.target.value)}
                    >
                      <option value="">Select picture...</option>
                      {referencePictures.map((picture) => (
                        <option key={picture.id} value={picture.id}>
                          {picture.id}
                        </option>
                      ))}
                    </select>
                    
                    {/* Picture Preview */}
                    {referencePictureId && (
                      <div className="reference-preview" style={{ marginTop: '8px', textAlign: 'center' }}>
                        <img 
                          src={`${API_BASE_URL}/Avatar/References/${referencePictureId}.jpg?t=${Date.now()}`}
                          alt="Reference"
                          style={{ maxWidth: '200px', maxHeight: '200px', borderRadius: '8px', border: '2px solid #3c4043' }}
                          onError={(e) => {
                            e.target.onerror = null;
                            e.target.src = `${API_BASE_URL}/Avatar/References/${referencePictureId}.jpg?t=${Date.now()}`;
                          }}
                        />
                      </div>
                    )}
                    
                    <label className="action-btn secondary full-width">
                      📸 Upload Picture
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handlePictureUpload}
                        style={{ display: 'none' }}
                      />
                    </label>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Error Toast */}
      {error && (
        <div className="error-toast">
          <div className="toast-icon">⚠️</div>
          <div className="toast-content">
            <div className="toast-title">Error</div>
            <div className="toast-message">{error}</div>
          </div>
          <button 
            className="toast-close"
            onClick={() => setError(null)}
          >
            ✕
          </button>
        </div>
      )}
      
      {/* Conversation History (Collapsible Bottom Panel) */}
      {conversationHistory.length > 0 && (
        <div className="history-panel">
          <div className="history-header">
            <h4>💬 Conversation History ({conversationHistory.length})</h4>
            <button 
              className="clear-history-btn"
              onClick={() => setConversationHistory([])}
            >
              🗑️ Clear
            </button>
          </div>
          <div className="history-messages">
            {conversationHistory.map((conv, idx) => (
              <div key={idx} className="history-message">
                <div className="message-user">
                  <span className="message-avatar">👤</span>
                  <div className="message-content">
                    <div className="message-meta">
                      You • {conv.timestamp.toLocaleTimeString()}
                    </div>
                    <div className="message-text">{conv.user}</div>
                  </div>
                </div>
                <div className="message-ai">
                  <span className="message-avatar">🤖</span>
                  <div className="message-content">
                    <div className="message-meta">
                      AI Assistant • {conv.timestamp.toLocaleTimeString()}
                    </div>
                    <div className="message-text">{conv.ai}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Hidden audio element for reference playback */}
      <audio ref={referencePlayerRef} style={{ display: 'none' }} />
    </div>
  );
};

export default LargeVideoAgent;
