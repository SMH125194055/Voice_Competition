import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';
import './MeetingAgent.css';

const API_BASE_URL = 'http://localhost:8000';

const MeetingAgent = () => {
  // State management
  const [isProcessing, setIsProcessing] = useState(false);
  const [isAISpeaking, setIsAISpeaking] = useState(false);
  const [isUserSpeaking, setIsUserSpeaking] = useState(false);
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
  
  // Avatar settings
  const [enableAvatar, setEnableAvatar] = useState(true);
  const [referencePictureId, setReferencePictureId] = useState(null);
  const [referencePictures, setReferencePictures] = useState([]);
  const [avatarVideoUrl, setAvatarVideoUrl] = useState(null);
  const [userVideoStream, setUserVideoStream] = useState(null);
  const avatarVideoRef = useRef(null);
  const userVideoRef = useRef(null);
  
  // Audio player states
  const [isPlayingReference, setIsPlayingReference] = useState(false);
  const [referenceAudioProgress, setReferenceAudioProgress] = useState(0);
  const [referenceAudioDuration, setReferenceAudioDuration] = useState(0);
  
  // UI States
  const [showSettings, setShowSettings] = useState(false);
  const [showConversationLogs, setShowConversationLogs] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [userVideoMinimized, setUserVideoMinimized] = useState(false);
  const [aiVideoMinimized, setAiVideoMinimized] = useState(false);
  const [idleAvatarUrl, setIdleAvatarUrl] = useState(null);
  const [isCameraOn, setIsCameraOn] = useState(true);
  const [isMicOn, setIsMicOn] = useState(true);
  const [isGeneratingIdle, setIsGeneratingIdle] = useState(false);
  
  // VAD sensitivity
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
      setIsUserSpeaking(true);
      
      if ((isAISpeaking || isProcessing) && allowInterruption) {
        console.log('🛑 Interruption detected!');
        stopAISpeaking();
      }
      
      setStatus('Listening to you...');
    },
    onSpeechEnd: async (audio) => {
      console.log('🔇 Speech ended');
      setIsUserSpeaking(false);
      setStatus('Processing...');
      
      // First, quickly transcribe to check for voice commands
      try {
        const quickCheck = await fetch(`${API_BASE_URL}/stt/transcribe`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            audio: Array.from(new Uint8Array(await audio.arrayBuffer())),
            format: 'wav'
          })
        });
        
        if (quickCheck.ok) {
          const result = await quickCheck.json();
          const text = result.text || '';
          console.log('Quick transcription:', text);
          
          // Check for voice commands
          if (checkVoiceCommand(text)) {
            // Voice command detected, don't process further
            return;
          }
        }
      } catch (err) {
        console.log('Quick check failed, proceeding with normal flow');
      }
      
      // If not a voice command, proceed with normal processing
      processAudioDataStreaming(audio);
    },
    onVADMisfire: () => {
      console.log('❌ VAD misfire');
      setIsUserSpeaking(false);
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
      setStatus('Ready! Say "start meeting" or click Start button');
      setIsReady(true);
    }
  }, [vad.loading, vad.errored]);
  
  useEffect(() => {
    setIsListening(vad.listening);
    if (vad.listening && !isProcessing && !isAISpeaking) {
      setStatus('Listening...');
    }
  }, [vad.listening, isProcessing, isAISpeaking]);
  
  // Toggle camera on/off
  const toggleCamera = () => {
    if (userVideoStream) {
      const videoTrack = userVideoStream.getVideoTracks()[0];
      if (videoTrack) {
        if (isCameraOn) {
          videoTrack.stop();
          setIsCameraOn(false);
        } else {
          // Restart camera
          navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 }, audio: false })
            .then(stream => {
              setUserVideoStream(stream);
              if (userVideoRef.current) {
                userVideoRef.current.srcObject = stream;
              }
              setIsCameraOn(true);
            })
            .catch(err => console.log('Camera restart failed:', err));
        }
      }
    }
  };
  
  // Toggle mic on/off
  const toggleMic = () => {
    if (userVideoStream) {
      const audioTrack = userVideoStream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setIsMicOn(audioTrack.enabled);
      }
    }
  };
  
  // Generate idle animation
  const generateIdleAnimation = async () => {
    if (!referencePictureId || !enableAvatar) {
      setError('Please select a reference picture and enable avatar');
      return;
    }
    
    setIsGeneratingIdle(true);
    setStatus('Generating idle animation...');
    
    try {
      const response = await fetch(`${API_BASE_URL}/generate-idle-animation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          picture_id: referencePictureId,
          duration: 3  // 3 second idle animation
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        const idleUrl = `${API_BASE_URL}${data.idle_video_url}?t=${Date.now()}`;
        setIdleAvatarUrl(idleUrl);
        
        // Play idle animation immediately
        if (avatarVideoRef.current) {
          avatarVideoRef.current.src = idleUrl;
          avatarVideoRef.current.loop = true;
          avatarVideoRef.current.play().catch(e => console.log('Auto-play prevented'));
        }
        
        setStatus('Idle animation ready!');
        setTimeout(() => setStatus('Ready to start conversation'), 2000);
      } else {
        throw new Error('Failed to generate idle animation');
      }
    } catch (err) {
      console.error('Idle generation failed:', err);
      setError('Failed to generate idle animation');
      setStatus('Ready');
    } finally {
      setIsGeneratingIdle(false);
    }
  };
  
  // Initialize user camera for "meeting" view
  useEffect(() => {
    const initCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
          video: { width: 1280, height: 720 }, 
          audio: false 
        });
        setUserVideoStream(stream);
        if (userVideoRef.current) {
          userVideoRef.current.srcObject = stream;
        }
        setIsCameraOn(true);
      } catch (err) {
        console.log('Camera not available:', err);
        setIsCameraOn(false);
      }
    };
    
    initCamera();
    
    return () => {
      if (userVideoStream) {
        userVideoStream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);
  
  // Update user video stream when ref changes
  useEffect(() => {
    if (userVideoRef.current && userVideoStream) {
      userVideoRef.current.srcObject = userVideoStream;
    }
  }, [userVideoStream]);
  
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
  
  // Play audio chunk with word highlighting
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
                video.muted = false;
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
                  console.error('❌ Avatar video error:', e);
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);
                  resolve();
                }, { once: true });
                
                video.play().catch(err => {
                  console.error('❌ Failed to play avatar video:', err);
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);
                  playAudioOnly();
                });
                
              } else {
                playAudioOnly();
              }
            }, 100);
            
          } catch (error) {
            console.error('❌ Error creating avatar video:', error);
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
      
      // Show idle animation between chunks if available
      if (audioQueueRef.current.length > 0 && idleAvatarUrl && enableAvatar && avatarVideoRef.current) {
        console.log('⏸️ Showing idle animation between chunks...');
        avatarVideoRef.current.src = idleAvatarUrl;
        avatarVideoRef.current.loop = true;
        avatarVideoRef.current.muted = true;
        avatarVideoRef.current.play().catch(e => console.log('Idle play failed:', e));
        
        // Brief pause to show idle (200ms)
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    }
    
    isPlayingRef.current = false;
    setIsAISpeaking(false);
    setCurrentWordIndex(-1);
    
    // Return to idle animation after all chunks finish
    if (idleAvatarUrl && enableAvatar && avatarVideoRef.current) {
      console.log('🔄 Returning to idle animation after speech...');
      avatarVideoRef.current.src = idleAvatarUrl;
      avatarVideoRef.current.loop = true;
      avatarVideoRef.current.muted = true;
      avatarVideoRef.current.play().catch(e => console.log('Idle play failed:', e));
    }
    
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
    
    setStatus(isListening ? 'Listening...' : 'Ready');
    setChunkProgress({ current: 0, total: 0 });
  };
  
  // Stop AI speaking
  const stopAISpeaking = () => {
    console.log('🛑 Stopping AI speech...');
    
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
    
    setStatus(isListening ? 'Listening...' : 'Ready');
  };
  
  // Load reference voices and pictures
  useEffect(() => {
    loadReferenceVoices();
    loadReferencePictures();
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
        alert(`Reference voice saved!`);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Failed to upload reference voice:', error);
      alert('Failed to upload reference voice.');
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
        alert('Reference picture uploaded!');
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Failed to upload picture:', error);
      alert('Failed to upload reference picture.');
    }
  };
  
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    
    await uploadReferenceVoice(file);
    event.target.value = '';
  };
  
  // Check for voice commands
  const checkVoiceCommand = (text) => {
    const lowerText = text.toLowerCase().trim();
    
    // Start meeting command
    if (lowerText.includes('start meeting') || lowerText.includes('begin meeting')) {
      console.log('Voice command: START MEETING');
      if (!isListening) {
        toggleListening();
        setStatus('Meeting started via voice command!');
        setTimeout(() => setStatus('Listening...'), 2000);
      }
      return true;
    }
    
    // Stop meeting command
    if (lowerText.includes('stop meeting') || lowerText.includes('end meeting')) {
      console.log('Voice command: STOP MEETING');
      if (isListening) {
        toggleListening();
        setStatus('Meeting stopped via voice command!');
      }
      return true;
    }
    
    return false;
  };
  
  // Process audio with SSE streaming
  const processAudioDataStreaming = async (audioData) => {
    if (isProcessing || isAISpeaking) {
      return;
    }
    
    try {
      isInterruptedRef.current = false;
      
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
        const { done, value } = await reader.read();
        
        if (done) {
          break;
        }
        
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
              
              // Check for voice commands
              if (checkVoiceCommand(data.text)) {
                // Voice command detected, stop processing
                setIsProcessing(false);
                return;
              }
            }
            
            if (currentEvent === 'llm_complete' && data.text) {
              setCurrentPhase('llm');
              aiTextReceived = data.text;
              setCurrentAIText(data.text);
              setStatus('🤖 AI responding...');
            }
            
            if (data.audio) {
              if (isInterruptedRef.current) {
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
  
  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };
  
  // Cleanup
  useEffect(() => {
    return () => {
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
      
      if (userVideoStream) {
        userVideoStream.getTracks().forEach(track => track.stop());
      }
      
      audioQueueRef.current = [];
      isPlayingRef.current = false;
    };
  }, [userVideoStream]);
  
  return (
    <div className="meeting-agent" ref={containerRef}>
      {/* Top Navigation Bar */}
      <div className="meeting-nav">
        <div className="meeting-title">
          <span className="meeting-icon">🎙️</span>
          <h1>AI Voice Meeting</h1>
          <span className="meeting-status-badge">{status}</span>
        </div>
        
        <div className="meeting-actions">
          <button 
            className="nav-btn"
            onClick={toggleFullscreen}
            title="Toggle fullscreen"
          >
            {isFullscreen ? '⊗' : '⛶'}
          </button>
        </div>
      </div>
      
      {/* Main Meeting Area */}
      <div className="meeting-main">
        {/* Video Grid */}
        <div className={`video-grid ${showConversationLogs || showSettings ? 'with-conversation-panel' : ''}`}>
          {/* Human Participant Video */}
          {!userVideoMinimized && (
            <div className="video-container">
              <div className={`participant-video ${isUserSpeaking ? 'speaking' : ''}`}>
                {isCameraOn ? (
                  <video 
                    ref={userVideoRef}
                    autoPlay
                    playsInline
                    muted
                    className="video-element"
                  />
                ) : (
                  <div className="video-placeholder camera-off">
                    <div className="placeholder-icon">📹❌</div>
                    <p>Camera is off</p>
                  </div>
                )}
                <div className="video-overlay">
                  <div className="participant-name">
                    <span className="participant-icon">👤</span>
                    <span>You</span>
                    {isUserSpeaking && <span className="speaking-indicator">🎙️</span>}
                  </div>
                </div>
                {/* Video control buttons */}
                <div className="video-controls">
                  <button 
                    className={`video-control-btn camera-btn ${!isCameraOn ? 'off' : ''}`}
                    onClick={toggleCamera}
                    title={isCameraOn ? "Turn off camera" : "Turn on camera"}
                  >
                    {isCameraOn ? '📹' : '📹❌'}
                  </button>
                  <button 
                    className={`video-control-btn mic-btn ${!isMicOn ? 'off' : ''}`}
                    onClick={toggleMic}
                    title={isMicOn ? "Mute microphone" : "Unmute microphone"}
                  >
                    {isMicOn ? '🎤' : '🎤❌'}
                  </button>
                  <button 
                    className="video-control-btn minimize-btn"
                    onClick={() => setUserVideoMinimized(true)}
                    title="Minimize video"
                  >
                    ➖
                  </button>
                </div>
              </div>
              {/* Subtitle overlay for user - OUTSIDE video box */}
              {streamingUserWords.length > 0 && (
                <div className="subtitle-line transparent-bg">
                  {streamingUserWords.map((word, idx) => (
                    <span key={idx} className="subtitle-word">
                      {word}{' '}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {/* AI Avatar Video */}
          {!aiVideoMinimized && (
            <div className="video-container">
              <div className={`participant-video ${isAISpeaking ? 'speaking' : ''}`}>
                {enableAvatar && (avatarVideoUrl || idleAvatarUrl) ? (
                  <video 
                    ref={avatarVideoRef}
                    playsInline
                  loop={!isAISpeaking && idleAvatarUrl} 
                  autoPlay={!isAISpeaking && idleAvatarUrl}
                  className="video-element avatar-video"
                />
                ) : idleAvatarUrl ? (
                  <video 
                    ref={avatarVideoRef}
                    src={idleAvatarUrl}
                    playsInline
                    loop
                    autoPlay
                    muted
                    className="video-element avatar-video"
                  />
                ) : (
                  <div className="video-placeholder">
                    <div className="placeholder-avatar">
                      {isAISpeaking ? '🗣️' : '✨'}
                    </div>
                    <p>{isAISpeaking ? 'AI is speaking...' : 'Generate Idle Animation'}</p>
                    <button
                      className="generate-idle-placeholder-btn"
                      onClick={generateIdleAnimation}
                      disabled={!referencePictureId || !enableAvatar || isGeneratingIdle}
                    >
                      {isGeneratingIdle ? '⏳ Generating...' : '✨ Generate Now'}
                    </button>
                  </div>
                )}
                <div className="video-overlay">
                  <div className="participant-name">
                    <span className="participant-icon">🤖</span>
                    <span>AI Assistant</span>
                    {isAISpeaking && <span className="speaking-indicator">🔊</span>}
                  </div>
                </div>
                {/* Video control buttons */}
                <div className="video-controls">
                  <button 
                    className="video-control-btn minimize-btn"
                    onClick={() => setAiVideoMinimized(true)}
                    title="Minimize video"
                  >
                    ➖
                  </button>
                </div>
              </div>
              {/* Subtitle overlay for AI - OUTSIDE video box */}
              {streamingAIWords.length > 0 && (
                <div className="subtitle-line transparent-bg">
                  {streamingAIWords.map((word, idx) => (
                    <span 
                      key={idx} 
                      className={`subtitle-word ${idx === currentWordIndex ? 'highlighted' : idx < currentWordIndex ? 'spoken' : ''}`}
                    >
                      {word}{' '}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {/* Minimized videos restore buttons */}
          {userVideoMinimized && (
            <button 
              className="restore-video-btn user-restore"
              onClick={() => setUserVideoMinimized(false)}
            >
              👤 Restore Your Video
            </button>
          )}
          {aiVideoMinimized && (
            <button 
              className="restore-video-btn ai-restore"
              onClick={() => setAiVideoMinimized(false)}
            >
              🤖 Restore AI Video
            </button>
          )}
        </div>
        
        {/* Settings Panel - Only show when active */}
        {showSettings && (
        <div className="conversation-panel">
          <div className="panel-header">
            <h3>⚙️ Settings</h3>
            <button 
              className="panel-close-btn"
              onClick={() => setShowSettings(false)}
            >
              ✕
            </button>
          </div>
          
          <div className="panel-content">
            {/* Voice Mode */}
            <div className="setting-group">
              <label>Voice Mode:</label>
              <div className="toggle-capsule">
                <button 
                  className={`capsule-btn ${voiceMode === 'inference' ? 'active' : ''}`}
                  onClick={() => setVoiceMode('inference')}
                  disabled={isListening}
                >
                  🎙️ Inference
                </button>
                <button 
                  className={`capsule-btn ${voiceMode === 'real-time' ? 'active' : ''}`}
                  onClick={() => setVoiceMode('real-time')}
                  disabled={isListening}
                >
                  🎤 Real-Time
                </button>
              </div>
            </div>
            
            {/* Reference Voice */}
            {voiceMode === 'inference' && (
              <div className="setting-group">
                <label>Reference Voice:</label>
                <select
                  value={referenceVoiceId || ''}
                  onChange={(e) => setReferenceVoiceId(e.target.value)}
                  disabled={isListening}
                  className="setting-select"
                >
                  <option value="">Select voice...</option>
                  {referenceVoices.map((voice) => (
                    <option key={voice.id} value={voice.id}>
                      {voice.id}
                    </option>
                  ))}
                </select>
                
                <div className="button-group">
                  <button
                    className="setting-btn"
                    onClick={isRecordingReference ? stopReferenceRecording : startReferenceRecording}
                    disabled={isListening}
                  >
                    {isRecordingReference ? '⏹️ Stop' : '🎤 Record'}
                  </button>
                  
                  <label className="setting-btn">
                    📁 Upload
                    <input
                      type="file"
                      accept="audio/*"
                      onChange={handleFileUpload}
                      disabled={isListening}
                      style={{ display: 'none' }}
                    />
                  </label>
                  
                  <button
                    className="setting-btn"
                    onClick={() => {
                      if (referenceVoiceId) {
                        const audio = new Audio(`${API_BASE_URL}/reference-voices/${referenceVoiceId}/play`);
                        audio.play().catch(err => console.log('Play failed:', err));
                      }
                    }}
                    disabled={!referenceVoiceId || isListening}
                    title="Play selected voice"
                  >
                    ▶️ Play
                  </button>
                </div>
                
                {/* Inline Audio Player for Reference Voice */}
                {referenceVoiceId && (
                  <div className="inline-audio-player">
                    <audio 
                      controls 
                      src={`${API_BASE_URL}/reference-voices/${referenceVoiceId}/play`}
                      style={{ width: '100%', marginTop: '8px' }}
                    >
                      Your browser does not support audio playback.
                    </audio>
                  </div>
                )}
              </div>
            )}
            
            {/* Avatar Toggle */}
            <div className="setting-group">
              <label>Avatar Generation:</label>
              <div className="toggle-switch">
                <input
                  type="checkbox"
                  id="enable-avatar"
                  checked={enableAvatar}
                  onChange={(e) => setEnableAvatar(e.target.checked)}
                  disabled={isListening}
                />
                <label htmlFor="enable-avatar" className="switch-label">
                  <span className="switch-slider"></span>
                </label>
                <span className="toggle-text">
                  {enableAvatar ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
            
            {/* Reference Picture */}
            {enableAvatar && (
              <div className="setting-group">
                <label>Reference Picture:</label>
                <select
                  value={referencePictureId || ''}
                  onChange={(e) => setReferencePictureId(e.target.value)}
                  disabled={isListening}
                  className="setting-select"
                >
                  <option value="">Select picture...</option>
                  {referencePictures.map((pic) => (
                    <option key={pic.id} value={pic.id}>
                      {pic.id}
                    </option>
                  ))}
                </select>
                
                <div className="button-group">
                  <label className="setting-btn upload-btn">
                    📸 Upload Picture
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handlePictureUpload}
                      disabled={isListening}
                      style={{ display: 'none' }}
                    />
                  </label>
                  
                </div>
                
                {/* Image Preview - Always show when picture is selected */}
                {referencePictureId && (
                  <div className="image-preview">
                    <img 
                      src={`${API_BASE_URL}/reference-pictures/${referencePictureId}/view`}
                      alt="Reference Picture"
                      onError={(e) => {
                        console.error('Image load error');
                        e.target.style.display = 'none';
                      }}
                    />
                  </div>
                )}
                
                {/* Generate Idle Animation Button */}
                <button
                  className="setting-btn idle-btn"
                  onClick={generateIdleAnimation}
                  disabled={!referencePictureId || !enableAvatar || isListening || isGeneratingIdle}
                  style={{ width: '100%', marginTop: '12px' }}
                >
                  {isGeneratingIdle ? '⏳ Generating...' : '✨ Generate Idle Animation'}
                </button>
                
                {idleAvatarUrl && (
                  <div className="idle-status">
                    ✅ Idle animation ready
                  </div>
                )}
              </div>
            )}
            
            {/* Allow Interruption */}
            <div className="setting-group">
              <label>Allow Interruption:</label>
              <div className="toggle-switch">
                <input
                  type="checkbox"
                  id="allow-interruption"
                  checked={allowInterruption}
                  onChange={(e) => setAllowInterruption(e.target.checked)}
                  disabled={isListening}
                />
                <label htmlFor="allow-interruption" className="switch-label">
                  <span className="switch-slider"></span>
                </label>
                <span className="toggle-text">
                  {allowInterruption ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        </div>
        )}
        
        {/* Conversation Logs Panel - Only show when active */}
        {showConversationLogs && (
        <div className="conversation-panel">
          <div className="panel-header">
            <h3>💬 Conversation</h3>
            <button 
              className="panel-close-btn"
              onClick={() => setShowConversationLogs(false)}
            >
              ✕
            </button>
          </div>
          
          <div className="panel-content conversation-logs">
            {conversationHistory.length === 0 ? (
              <div className="empty-logs">
                <div className="empty-icon">🎙️</div>
                <p>No messages yet</p>
                <p>Start conversation below</p>
              </div>
            ) : (
              conversationHistory.map((conv, idx) => (
                <div key={idx} className="conversation-message-pair">
                  <div className="message user-message">
                    <div className="message-header">
                      <span>👤 You</span>
                      <span className="message-time">
                        {conv.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="message-text">{conv.user}</div>
                  </div>
                  
                  <div className="message ai-message">
                    <div className="message-header">
                      <span>🤖 AI</span>
                      <span className="message-time">
                        {conv.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="message-text">{conv.ai}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        )}
      </div>
      
      {/* Bottom Control Bar */}
      <div className="meeting-controls">
        <div className="controls-left">
          <button 
            className={`control-btn ${showSettings ? 'active' : ''}`}
            onClick={() => {
              setShowSettings(!showSettings);
              if (!showSettings) setShowConversationLogs(false); // Close conversation when opening settings
            }}
            title="Settings"
          >
            ⚙️
          </button>
          
          <button 
            className={`control-btn ${showConversationLogs ? 'active' : ''}`}
            onClick={() => {
              setShowConversationLogs(!showConversationLogs);
              if (!showConversationLogs) setShowSettings(false); // Close settings when opening conversation
            }}
            title="Conversation logs"
          >
            💬
          </button>
        </div>        
        <div className="controls-center">
          <button
            className={`main-control-btn ${isListening ? 'listening' : ''}`}
            onClick={toggleListening}
            disabled={!isReady || isProcessing}
          >
            {isListening ? (
              <>
                <span className="btn-icon">⏹️</span>
                <span className="btn-text">Stop</span>
              </>
            ) : (
              <>
                <span className="btn-icon">▶️</span>
                <span className="btn-text">Start</span>
              </>
            )}
          </button>
          
          {chunkProgress.total > 0 && (
            <div className="progress-indicator">
              <span>{chunkProgress.current}/{chunkProgress.total}</span>
            </div>
          )}
        </div>
        
        <div className="controls-right">
          {currentPhase && (
            <div className="phase-dots">
              <span className={`dot ${currentPhase === 'vad' ? 'active' : currentPhase !== 'vad' && currentPhase !== '' ? 'done' : ''}`} title="VAD"></span>
              <span className={`dot ${currentPhase === 'transcription' ? 'active' : ['llm', 'tts', 'complete'].includes(currentPhase) ? 'done' : ''}`} title="STT"></span>
              <span className={`dot ${currentPhase === 'llm' ? 'active' : ['tts', 'complete'].includes(currentPhase) ? 'done' : ''}`} title="LLM"></span>
              <span className={`dot ${['tts', 'complete'].includes(currentPhase) ? 'active' : ''}`} title="TTS"></span>
            </div>
          )}
        </div>
      </div>
      
      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)}>✕</button>
        </div>
      )}
    </div>
  );
};

export default MeetingAgent;

