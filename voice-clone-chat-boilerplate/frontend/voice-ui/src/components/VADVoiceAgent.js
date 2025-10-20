import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useMicVAD } from '@ricky0123/vad-react';
import './VADVoiceAgent.css';

const API_BASE_URL = 'http://localhost:8001';

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
  
  // NEW: Voice mode and interruption settings
  const [voiceMode, setVoiceMode] = useState('inference'); // 'inference' or 'real-time'
  const [allowInterruption, setAllowInterruption] = useState(true);
  const [referenceVoiceId, setReferenceVoiceId] = useState(null);
  const [referenceVoices, setReferenceVoices] = useState([]);
  const [isRecordingReference, setIsRecordingReference] = useState(false);
  const [showReferenceModal, setShowReferenceModal] = useState(false);
  const [isSettingsExpanded, setIsSettingsExpanded] = useState(true); // Settings panel expanded by default
  
  // NEW: Avatar settings
  const [enableAvatar, setEnableAvatar] = useState(true); // Enable/disable avatar generation
  const [referencePictureId, setReferencePictureId] = useState(null);
  const [referencePictures, setReferencePictures] = useState([]);
  const [avatarVideo, setAvatarVideo] = useState(null); // Store generated avatar video
  const [isGeneratingAvatar, setIsGeneratingAvatar] = useState(false);
  const [avatarVideoUrl, setAvatarVideoUrl] = useState(null); // Current video URL
  const avatarVideoRef = useRef(null); // Reference to avatar video element
  
  // Audio player states
  const [isPlayingReference, setIsPlayingReference] = useState(false);
  const [referenceAudioProgress, setReferenceAudioProgress] = useState(0);
  const [referenceAudioDuration, setReferenceAudioDuration] = useState(0);
  
  // VAD sensitivity fixed to HIGH for best noise resistance
  const vadSensitivity = 'high';
  
  // Refs
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const abortControllerRef = useRef(null);
  const currentAudioRef = useRef(null);
  const referenceRecorderRef = useRef(null);
  const referenceAudioChunksRef = useRef([]);
  const isInterruptedRef = useRef(false); // Flag to track if current stream was interrupted
  const referencePlayerRef = useRef(null); // Reference audio player
  
  // VAD sensitivity configurations - Higher thresholds = Less sensitive (better for noisy environments)
  const vadConfigs = useMemo(() => ({
    low: {  // Very sensitive - will detect quiet speech but may trigger on noise
      positiveSpeechThreshold: 0.5,
      negativeSpeechThreshold: 0.35,
      minSpeechFrames: 3,
      redemptionFrames: 8,
    },
    medium: {  // Balanced - good for normal environments
      positiveSpeechThreshold: 0.7,
      negativeSpeechThreshold: 0.5,
      minSpeechFrames: 5,
      redemptionFrames: 8,
    },
    high: {  // Less sensitive - better for noisy environments, requires louder/clearer speech
      positiveSpeechThreshold: 0.85,
      negativeSpeechThreshold: 0.65,
      minSpeechFrames: 8,
      redemptionFrames: 10,
    },
  }), []);
  
  // VAD Configuration with dynamic sensitivity
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
      console.log('🎤 Speech detected! (Sensitivity:', vadSensitivity, ')');
      
      // Handle interruption if AI is speaking OR processing and interruption is allowed
      if ((isAISpeaking || isProcessing) && allowInterruption) {
        console.log('🛑 Interruption detected! Stopping AI/Processing...');
        stopAISpeaking(); // This will also stop processing
      }
      
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
      console.log('❌ VAD misfire (Sensitivity:', vadSensitivity, ')');
      setIsSpeaking(false);
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
  
  // Play audio chunk with word highlighting (and avatar video if available)
  const playAudioChunk = async (base64Audio, chunkWords, startWordIndex, avatarVideoBase64 = null, hasAvatar = false) => {
    return new Promise((resolve) => {
      try {
        // 🎬 NEW: If avatar video is available, play it instead of audio
        if (hasAvatar && avatarVideoBase64) {
          console.log('🎬 Playing avatar video chunk with embedded audio...');
          
          try {
            // Convert base64 to blob
            const byteCharacters = atob(avatarVideoBase64);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
              byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'video/mp4' });
            const videoUrl = URL.createObjectURL(blob);
            
            console.log('✅ Avatar video blob created, size:', blob.size);
            
            // Update avatar video display URL
            setAvatarVideoUrl(videoUrl);
            
            // Use the DISPLAYED video element (avatarVideoRef) to play
            // Wait a bit for React to update the video element
            setTimeout(() => {
              if (avatarVideoRef.current) {
                console.log('🎬 Using displayed video element for playback');
                
                const video = avatarVideoRef.current;
                video.muted = false;  // ✅ Enable audio from video
                video.src = videoUrl;
                video.load();
                
                currentAudioRef.current = video;  // Track as current playing media
                
                video.addEventListener('loadedmetadata', () => {
                  const duration = video.duration * 1000;
                  const wordDelay = chunkWords.length > 0 ? duration / chunkWords.length : 0;
                  
                  console.log(`🎬 Video loaded, duration: ${video.duration}s`);
                  
                  // Highlight words
                  chunkWords.forEach((_, idx) => {
                    setTimeout(() => {
                      const newIndex = startWordIndex + idx;
                      setCurrentWordIndex(newIndex);
                      
                      setTimeout(() => {
                        const highlightedWord = document.querySelector('.text-scroll-content .word.highlighted');
                        if (highlightedWord) {
                          highlightedWord.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        }
                      }, 50);
                    }, wordDelay * idx);
                  });
                  
                  setTimeout(() => {
                    setCurrentWordIndex(-1);
                  }, duration);
                }, { once: true });
                
                video.addEventListener('ended', () => {
                  console.log('🎬 Avatar video chunk finished');
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);  // Clean up blob URL
                  resolve();
                }, { once: true });
                
                video.addEventListener('error', (e) => {
                  console.error('❌ Avatar video error:', e);
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);
                  resolve();
                }, { once: true });
                
                // Play the video (audio will come from video)
                video.play().then(() => {
                  console.log('🎬 Avatar video chunk playing with audio');
                }).catch(err => {
                  console.error('❌ Failed to play avatar video:', err);
                  currentAudioRef.current = null;
                  URL.revokeObjectURL(videoUrl);
                  // Fall back to audio-only
                  playAudioOnly();
                });
                
              } else {
                console.warn('⚠️ Avatar video ref not available, falling back to audio');
                playAudioOnly();
              }
            }, 100);  // Small delay for React update
            
          } catch (error) {
            console.error('❌ Error creating avatar video:', error);
            // Fall back to audio-only
            playAudioOnly();
          }
        } else {
          // No avatar - play audio only
          console.log('🔊 No avatar video, playing audio only');
          playAudioOnly();
        }
        
        // Helper function for audio-only playback
        function playAudioOnly() {
          const audio = new Audio(`data:audio/wav;base64,${base64Audio}`);
          currentAudioRef.current = audio;
          
          audio.addEventListener('loadedmetadata', () => {
            const duration = audio.duration * 1000;
            const wordDelay = chunkWords.length > 0 ? duration / chunkWords.length : 0;
            
            chunkWords.forEach((_, idx) => {
              setTimeout(() => {
                const newIndex = startWordIndex + idx;
                setCurrentWordIndex(newIndex);
                
                setTimeout(() => {
                  const highlightedWord = document.querySelector('.text-scroll-content .word.highlighted');
                  if (highlightedWord) {
                    highlightedWord.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                  }
                }, 50);
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
          console.log('🔊 Audio playing (no avatar)');
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
      
      // Add chunk words to display
      const chunkWords = chunk.text.split(' ');
      setStreamingAIWords(prev => [...prev, ...chunkWords]);
      
      // Play audio (or avatar video) with highlighting
      // 🎬 Pass avatar video data if available
      await playAudioChunk(chunk.audio, chunkWords, wordIndex, chunk.avatarVideo, chunk.hasAvatar);
      wordIndex += chunkWords.length;
      
      // Update progress
      setChunkProgress(prev => ({ ...prev, current: prev.current + 1 }));
    }
    
    isPlayingRef.current = false;
    setIsAISpeaking(false);
    setCurrentWordIndex(-1);
    
    // Save to history - Use ONLY transcription and LLM response (NOT streaming words)
    // This ensures we get the complete, original text from backend
    if (currentUserText && currentAIText) {
      const newConversation = {
        user: currentUserText,
        ai: currentAIText,
        timestamp: new Date()
      };
      
      console.log('💾 Saving complete conversation to history (from transcription/LLM):', {
        userLength: currentUserText.length,
        aiLength: currentAIText.length,
        userPreview: currentUserText.substring(0, 50),
        aiPreview: currentAIText.substring(0, 50)
      });
      
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
    } else {
      console.warn('⚠️ Cannot save conversation: missing user or AI text', {
        hasUserText: !!currentUserText,
        hasAIText: !!currentAIText
      });
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
    console.log('🛑 Stopping AI speech completely...');
    
    // Set interruption flag to prevent new chunks from being processed
    isInterruptedRef.current = true;
    
    // ⚠️ CRITICAL: Abort the SSE connection to stop backend from sending more chunks
    if (abortControllerRef.current) {
      console.log('⚠️ Aborting SSE stream...');
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    // Stop current audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    
    // Stop avatar video
    if (avatarVideoRef.current) {
      avatarVideoRef.current.pause();
      avatarVideoRef.current.currentTime = 0;
    }
    
    // Clear queue immediately
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    setIsAISpeaking(false);
    setIsProcessing(false);
    setIsGeneratingAvatar(false);
    setCurrentWordIndex(-1);
    setChunkProgress({ current: 0, total: 0 });
    setCurrentPhase('');
    
    // Save interrupted conversation with COMPLETE AI response from backend (NO [interrupted] tag)
    if (currentUserText && currentAIText) {
      // Use currentAIText which contains the COMPLETE response from backend
      // Show full response even if voice was interrupted
      const partialConv = {
        user: currentUserText,
        ai: currentAIText, // Complete LLM response WITHOUT [interrupted] tag
        timestamp: new Date()
      };
      
      console.log('💾 Saving interrupted conversation (complete LLM response - no tag):', {
        userLength: currentUserText.length,
        aiLength: currentAIText.length,
        aiTextPreview: currentAIText.substring(0, 50) + '...'
      });
      
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
  
  // ============================================
  // REFERENCE VOICE MANAGEMENT FUNCTIONS
  // ============================================
  
  // Load reference voices and pictures on component mount
  useEffect(() => {
    loadReferenceVoices();
    loadReferencePictures();
  }, []);
  
  const loadReferenceVoices = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/list-reference-voices`);
      const data = await response.json();
      setReferenceVoices(data.voices || []);
      
      // Auto-select first voice if in inference mode and no voice selected
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
      console.log('🎙️ Recording reference voice...');
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('Failed to access microphone. Please check permissions.');
    }
  };
  
  const stopReferenceRecording = () => {
    if (referenceRecorderRef.current && referenceRecorderRef.current.state !== 'inactive') {
      referenceRecorderRef.current.stop();
      setIsRecordingReference(false);
      console.log('🛑 Stopped recording reference voice');
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
        console.log('✅ Reference voice uploaded:', data.reference_voice_id);
        await loadReferenceVoices();
        setReferenceVoiceId(data.reference_voice_id);
        alert(`Reference voice saved! Duration: ${data.duration}s`);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Failed to upload reference voice:', error);
      alert('Failed to upload reference voice. Please try again.');
    }
  };
  
  const deleteReferenceVoice = async (voiceId) => {
    if (!window.confirm('Delete this reference voice?')) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/delete-reference-voice/${voiceId}`, {
        method: 'DELETE'
      });
      
      const data = await response.json();
      
      if (data.success) {
        console.log('🗑️ Deleted reference voice:', voiceId);
        await loadReferenceVoices();
        
        // Clear selection if deleted voice was selected
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
    
    console.log('📤 Uploading file:', file.name);
    await uploadReferenceVoice(file);
    
    // Reset file input
    event.target.value = '';
  };
  
  // Initialize reference audio player
  const initializeReferencePlayer = () => {
    if (!referenceVoiceId || !referencePlayerRef.current) return;
    
    const voice = referenceVoices.find(v => v.id === referenceVoiceId);
    if (!voice) return;
    
    // Add timestamp to force reload and prevent caching issues
    const audioUrl = `${API_BASE_URL}/audio/reference_voices/${voice.filename}?t=${Date.now()}`;
    
    // Reset player state
    setIsPlayingReference(false);
    setReferenceAudioProgress(0);
    setReferenceAudioDuration(0);
    
    // Load new audio
    referencePlayerRef.current.src = audioUrl;
    referencePlayerRef.current.load(); // Force reload
    
    // Set up event listeners
    referencePlayerRef.current.onloadedmetadata = () => {
      setReferenceAudioDuration(referencePlayerRef.current.duration);
      console.log('🎵 Audio loaded:', voice.id, 'Duration:', referencePlayerRef.current.duration);
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
    
    referencePlayerRef.current.onerror = (e) => {
      console.error('🔴 Audio player error:', e);
      setIsPlayingReference(false);
      // Retry loading
      setTimeout(() => {
        if (referencePlayerRef.current) {
          referencePlayerRef.current.load();
        }
      }, 500);
    };
  };
  
  // Play/pause reference voice
  const togglePlayReferenceVoice = () => {
    if (!referencePlayerRef.current) return;
    
    if (isPlayingReference) {
      referencePlayerRef.current.pause();
    } else {
      // Reload audio from start if it's stuck or ended
      if (referencePlayerRef.current.ended || referencePlayerRef.current.error) {
        console.log('🔄 Reloading stuck audio...');
        initializeReferencePlayer();
        // Wait for audio to load before playing
        setTimeout(() => {
          if (referencePlayerRef.current) {
            referencePlayerRef.current.play().catch(err => {
              console.error('Play error:', err);
            });
          }
        }, 200);
      } else {
        referencePlayerRef.current.play().catch(err => {
          console.error('Play error:', err);
          // If play fails, try reloading
          initializeReferencePlayer();
        });
      }
    }
  };
  
  // Seek in reference audio
  const seekReferenceAudio = (time) => {
    if (!referencePlayerRef.current) return;
    referencePlayerRef.current.currentTime = time;
    setReferenceAudioProgress(time);
  };
  
  // Stop reference audio
  const stopReferenceAudio = () => {
    if (!referencePlayerRef.current) return;
    referencePlayerRef.current.pause();
    referencePlayerRef.current.currentTime = 0;
    setIsPlayingReference(false);
    setReferenceAudioProgress(0);
  };
  
  // Initialize player when reference voice changes
  useEffect(() => {
    if (referenceVoiceId && referencePlayerRef.current) {
      initializeReferencePlayer();
    }
  }, [referenceVoiceId, referenceVoices]);
  
  // ============================================
  // REFERENCE PICTURE MANAGEMENT FUNCTIONS
  // ============================================
  
  const loadReferencePictures = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/list-reference-pictures`);
      const data = await response.json();
      setReferencePictures(data.pictures || []);
      
      // Auto-select first picture if enabled and no picture selected
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
        console.log('✅ Picture uploaded:', data.reference_picture_id);
        await loadReferencePictures();
        setReferencePictureId(data.reference_picture_id);
        alert('Reference picture uploaded successfully!');
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Failed to upload reference picture:', error);
      alert('Failed to upload reference picture. Please try again.');
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
        console.log('🗑️ Deleted reference picture:', pictureId);
        await loadReferencePictures();
        
        // Clear selection if deleted picture was selected
        if (referencePictureId === pictureId) {
          setReferencePictureId(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete reference picture:', error);
      alert('Failed to delete reference picture.');
    }
  };
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      console.log('🧹 Cleaning up VAD Voice Agent...');
      
      // Stop and cleanup reference audio player
      if (referencePlayerRef.current) {
        referencePlayerRef.current.pause();
        referencePlayerRef.current.src = '';
      }
      
      // Stop current AI audio
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
        currentAudioRef.current = null;
      }
      
      // Abort any ongoing SSE stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      
      // Stop reference recording if active
      if (referenceRecorderRef.current && referenceRecorderRef.current.state !== 'inactive') {
        referenceRecorderRef.current.stop();
      }
      
      // Clear audio queue
      audioQueueRef.current = [];
      isPlayingRef.current = false;
      
      console.log('✅ Cleanup complete');
    };
  }, []);
  
  // Process audio with SSE streaming
  const processAudioDataStreaming = async (audioData) => {
    if (isProcessing || isAISpeaking) {
      console.log('⏭️ Busy, skipping');
      return;
    }
    
    try {
      // Reset interruption flag for new conversation
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
      formData.append('voice_mode', voiceMode);
      formData.append('allow_interruption', allowInterruption.toString());
      
      // Add reference voice ID if in inference mode
      if (voiceMode === 'inference' && referenceVoiceId) {
        formData.append('reference_voice_id', referenceVoiceId);
      }
      
      // Add avatar settings
      formData.append('enable_avatar', enableAvatar.toString());
      if (enableAvatar && referencePictureId) {
        formData.append('reference_picture_id', referencePictureId);
      }
      
      console.log(`🎙️ Voice mode: ${voiceMode}, Interruption: ${allowInterruption}, Avatar: ${enableAvatar}`);
      
      abortControllerRef.current = new AbortController();
      
      // Use avatar stream endpoint if avatar is enabled
      const endpoint = enableAvatar ? '/vad-chat-avatar-stream' : '/vad-chat-voice-stream';
      
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
        
        let currentEvent = '';
        
        for (const line of lines) {
          // Track the current event type
          if (line.startsWith('event:')) {
            currentEvent = line.substring(6).trim();
            continue;
          }
          
          if (line.startsWith('data:')) {
            const data = JSON.parse(line.substring(6).trim());
            
            // VAD complete
            if (data.has_speech !== undefined) {
              setCurrentPhase('vad');
              setStatus(`✅ Speech detected (${data.duration}s)`);
            }
            
            // User transcription - ONLY from transcription_complete event
            if (currentEvent === 'transcription_complete' && data.text) {
              setCurrentPhase('transcription');
              userTextReceived = data.text;
              setCurrentUserText(data.text);
              setStatus('📝 You said...');
              
              // Display user text immediately (no streaming delay)
              const words = data.text.split(' ');
              setStreamingUserWords(words);
              console.log('💬 USER TRANSCRIPTION (from transcription_complete event):', data.text);
              console.log('🔍 userTextReceived is now:', userTextReceived);
            }
            
            // AI response - ONLY from llm_complete event
            if (currentEvent === 'llm_complete' && data.text) {
              setCurrentPhase('llm');
              aiTextReceived = data.text;
              setCurrentAIText(data.text);
              setStatus('🤖 AI responding...');
              console.log('🤖 LLM RESPONSE (from llm_complete event):', data.text);
              console.log('🔍 Check if different from user:', {
                user: userTextReceived,
                ai: data.text,
                areSame: userTextReceived === data.text
              });
            }
            
            // TTS chunks (with optional avatar video)
            if (data.audio) {
              // ⚠️ Check if stream was interrupted - skip adding chunks if true
              if (isInterruptedRef.current) {
                console.log('⏭️ Skipping chunk due to interruption');
                return; // Stop processing this stream
              }
              
              setCurrentPhase('tts');
              setChunkProgress({ current: data.chunk_index, total: data.total_chunks });
              
              // 🎬 Update status based on avatar availability
              if (data.has_avatar && data.avatar_video) {
                setStatus(`🎬 Avatar speaking (${data.chunk_index + 1})...`);
                console.log(`🎬 Chunk ${data.chunk_index + 1} has avatar video (${data.avatar_video.length} bytes base64)`);
              } else {
                setStatus(`🔊 Speaking (${data.chunk_index + 1})...`);
              }
              
              // Add to queue with avatar video if available
              audioQueueRef.current.push({
                audio: data.audio,
                text: data.text,
                words: data.words,
                avatarVideo: data.avatar_video || null,  // 🎬 NEW: Avatar video chunk
                hasAvatar: data.has_avatar || false
              });
              
              if (!isPlayingRef.current) {
                processAudioQueue();
              }
            }
            
            // Avatar error handling (chunks are handled in tts_chunk processing)
            if (currentEvent === 'avatar_error') {
              console.error('❌ Avatar generation error:', data.error);
              setIsGeneratingAvatar(false);
            }
            
            // Complete
            if (data.message === 'Conversation complete') {
              console.log('🎉 Complete!');
              setCurrentPhase('complete');
              setIsGeneratingAvatar(false);
            }
            
            // Errors
            if (data.error) {
              console.error('❌ Server error:', data.error);
              setError(data.error);
              setStatus('Error occurred');
              setIsGeneratingAvatar(false);
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
      
      {/* Settings Panel - Collapsible */}
      <div className={`settings-panel ${isSettingsExpanded ? 'expanded' : 'collapsed'}`}>
        <div className="settings-header" onClick={() => setIsSettingsExpanded(!isSettingsExpanded)}>
          <h3>⚙️ Settings</h3>
          <button className="settings-toggle-btn">
            {isSettingsExpanded ? '▲ Hide' : '▼ Show'}
          </button>
          </div>
          
        {isSettingsExpanded && (
          <div className="settings-content">
            {/* Voice Mode Toggle */}
            <div className="setting-group">
              <label className="setting-label">Voice Mode:</label>
              <div className="toggle-capsule">
          <button 
                  className={`capsule-btn ${voiceMode === 'inference' ? 'active' : ''}`}
                  onClick={() => setVoiceMode('inference')}
                  disabled={isListening || isProcessing || isAISpeaking}
                >
                  🎙️ Inference Voice
          </button>
          <button 
                  className={`capsule-btn ${voiceMode === 'real-time' ? 'active' : ''}`}
                  onClick={() => setVoiceMode('real-time')}
                  disabled={isListening || isProcessing || isAISpeaking}
                >
                  🎤 Real-Time Voice
          </button>
              </div>
              <div className="setting-description">
                {voiceMode === 'inference' 
                  ? '✓ Using pre-recorded reference voice for AI responses' 
                  : '✓ Using your current voice for AI responses'}
        </div>
      </div>
      
            {/* Reference Voice Management (shown only in inference mode) */}
            {voiceMode === 'inference' && (
              <div className="setting-group">
                <label className="setting-label">Reference Voice:</label>
                
                {/* Recording Prompt */}
                {!isRecordingReference && referenceVoices.length === 0 && (
                  <div className="recording-prompt">
                    <p>📝 <strong>Record your reference voice:</strong></p>
                    <p>Say something like: "Hello, this is my voice for testing the AI assistant. I'm speaking clearly and naturally."</p>
                    <p>Speak for <strong>3-5 seconds</strong> in a quiet environment.</p>
            </div>
                )}
                
                <div className="reference-voice-controls">
                  <select
                    className="reference-voice-select"
                    value={referenceVoiceId || ''}
                    onChange={(e) => setReferenceVoiceId(e.target.value)}
                    disabled={isListening || isProcessing || isAISpeaking}
                  >
                    <option value="">Select a reference voice...</option>
                    {referenceVoices.map((voice) => (
                      <option key={voice.id} value={voice.id}>
                        {voice.id} ({(voice.size / 1024).toFixed(0)}KB)
                      </option>
                    ))}
                  </select>
                  
                  <button
                    className="btn-record-ref"
                    onClick={isRecordingReference ? stopReferenceRecording : startReferenceRecording}
                    disabled={isListening || isProcessing || isAISpeaking}
                  >
                    {isRecordingReference ? '⏹️ Stop' : '🎤 Record'}
                  </button>
                  
                  <label className="btn-upload-ref" title="Upload audio file">
                    📁 Upload
                    <input
                      type="file"
                      accept="audio/*"
                      onChange={handleFileUpload}
                      disabled={isListening || isProcessing || isAISpeaking}
                      style={{ display: 'none' }}
                    />
                  </label>
                  
                  {referenceVoiceId && (
                    <button
                      className="btn-delete-ref"
                      onClick={() => deleteReferenceVoice(referenceVoiceId)}
                      disabled={isListening || isProcessing || isAISpeaking}
                      title="Delete reference voice"
                    >
                      🗑️
                    </button>
                  )}
          </div>
          
                {/* Audio Player for Reference Voice */}
                {referenceVoiceId && (
                  <div className="reference-audio-player">
                    <audio ref={referencePlayerRef} style={{ display: 'none' }} />
                    
                    <div className="player-controls">
                      <button
                        className="player-btn play-pause-btn"
                        onClick={togglePlayReferenceVoice}
                        disabled={isListening || isProcessing || isAISpeaking}
                        title={isPlayingReference ? "Pause" : "Play"}
                      >
                        {isPlayingReference ? '⏸️' : '▶️'}
                      </button>
                      
                      <div className="player-timeline">
                        <input
                          type="range"
                          min="0"
                          max={referenceAudioDuration || 100}
                          value={referenceAudioProgress}
                          onChange={(e) => seekReferenceAudio(parseFloat(e.target.value))}
                          className="timeline-slider"
                          disabled={isListening || isProcessing || isAISpeaking}
                        />
                        <div className="player-time">
                          <span className="current-time">
                            {Math.floor(referenceAudioProgress / 60)}:{String(Math.floor(referenceAudioProgress % 60)).padStart(2, '0')}
                          </span>
                          <span className="duration-time">
                            {Math.floor(referenceAudioDuration / 60)}:{String(Math.floor(referenceAudioDuration % 60)).padStart(2, '0')}
                          </span>
                        </div>
          </div>
          
                      <button
                        className="player-btn stop-btn"
                        onClick={stopReferenceAudio}
                        disabled={isListening || isProcessing || isAISpeaking}
                        title="Stop"
                      >
                        ⏹️
                      </button>
            </div>
                </div>
              )}
                
                {isRecordingReference && (
                  <div className="recording-indicator">
                    <span className="recording-dot"></span>
                    Recording... Speak clearly for 3-5 seconds.
            </div>
                )}
                
                {!referenceVoiceId && referenceVoices.length === 0 && !isRecordingReference && (
                  <div className="setting-description warning">
                    ⚠️ No reference voices available. Please record or upload one.
          </div>
                )}
        </div>
            )}
            
            {/* Allow Interruption Toggle */}
            <div className="setting-group">
              <label className="setting-label">Allow Interruption (VAD):</label>
              <div className="toggle-switch">
                <input
                  type="checkbox"
                  id="allow-interruption"
                  checked={allowInterruption}
                  onChange={(e) => setAllowInterruption(e.target.checked)}
                  disabled={isListening || isProcessing || isAISpeaking}
                />
                <label htmlFor="allow-interruption" className="switch-label">
                  <span className="switch-slider"></span>
                </label>
                <span className="toggle-text">
                  {allowInterruption ? 'Enabled' : 'Disabled'}
                </span>
            </div>
              <div className="setting-description">
                {allowInterruption 
                  ? '✓ AI will stop speaking when you start talking' 
                  : '✗ AI will continue speaking even if you talk'}
            </div>
            </div>
            
            {/* Avatar Generation Toggle */}
            <div className="setting-group">
              <label className="setting-label">Avatar Generation:</label>
              <div className="toggle-switch">
                <input
                  type="checkbox"
                  id="enable-avatar"
                  checked={enableAvatar}
                  onChange={(e) => setEnableAvatar(e.target.checked)}
                  disabled={isListening || isProcessing || isAISpeaking}
                />
                <label htmlFor="enable-avatar" className="switch-label">
                  <span className="switch-slider"></span>
                </label>
                <span className="toggle-text">
                  {enableAvatar ? 'Enabled 🎬' : 'Disabled'}
                </span>
              </div>
              <div className="setting-description">
                {enableAvatar 
                  ? '✓ AI will generate avatar video with response' 
                  : '✗ Voice-only mode (faster)'}
              </div>
            </div>
            
            {/* Reference Picture Management (shown only if avatar enabled) */}
            {enableAvatar && (
              <div className="setting-group">
                <label className="setting-label">Reference Picture:</label>
                
                {referencePictures.length === 0 && (
                  <div className="recording-prompt">
                    <p>📸 <strong>Upload your reference picture:</strong></p>
                    <p>Use a clear portrait photo (JPEG/PNG, min 256x256px)</p>
                  </div>
                )}
                
                <div className="reference-controls">
                  <select
                    className="reference-voice-select"
                    value={referencePictureId || ''}
                    onChange={(e) => setReferencePictureId(e.target.value)}
                    disabled={isListening || isProcessing || isAISpeaking}
                  >
                    <option value="">Select a reference picture...</option>
                    {referencePictures.map((picture) => (
                      <option key={picture.id} value={picture.id}>
                        {picture.id} ({picture.width}x{picture.height})
                      </option>
                    ))}
                  </select>
                  
                  {/* Picture preview */}
                  {referencePictureId && (
                    <div className="picture-preview">
                      <img 
                        src={`${API_BASE_URL}/avatar/reference_pictures/${referencePictures.find(p => p.id === referencePictureId)?.filename}`}
                        alt="Reference"
                        style={{width: '100px', height: '100px', objectFit: 'cover', borderRadius: '8px'}}
                      />
                    </div>
                  )}
                  
                  <div className="button-group">
                    {/* Upload picture button */}
                    <label className="btn-upload">
                      📸 Upload Picture
                      <input
                        type="file"
                        accept="image/jpeg,image/jpg,image/png"
                        onChange={handlePictureUpload}
                        disabled={isListening || isProcessing || isAISpeaking}
                        style={{ display: 'none' }}
                      />
                    </label>
                    
                    {/* Delete picture button */}
                    {referencePictureId && (
                      <button
                        className="btn-delete-ref"
                        onClick={() => deleteReferencePicture(referencePictureId)}
                        disabled={isListening || isProcessing || isAISpeaking}
                        title="Delete reference picture"
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                </div>
                
                {!referencePictureId && referencePictures.length === 0 && (
                  <div className="setting-description warning">
                    ⚠️ No reference pictures available. Please upload one.
                  </div>
                )}
              </div>
            )}
          </div>
        )}
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
            {/* Show avatar video if available, otherwise show emoji */}
            {enableAvatar && avatarVideoUrl ? (
              <video 
                ref={avatarVideoRef}
                playsInline
                className="avatar-video"
                style={{
                  width: '320px',
                  height: '320px',
                  borderRadius: '16px',
                  objectFit: 'cover',
                  position: 'absolute',
                  top: '-70px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  zIndex: 10,
                  boxShadow: '0 10px 40px rgba(0, 0, 0, 0.4)',
                  border: '3px solid rgba(255, 255, 255, 0.3)'
                }}
                onLoadedData={() => console.log('🎬 Avatar video loaded and ready')}
                onError={(e) => console.error('❌ Avatar video error:', e)}
              />
            ) : (
              <div className="circle-avatar">
                {isGeneratingAvatar ? '🎬' : '🤖'}
              </div>
            )}
            <div className="circle-label" style={{position: 'relative', zIndex: 20}}>
              {isGeneratingAvatar ? 'Generating Avatar...' : (avatarVideoUrl ? '🎬 Avatar' : 'AI Assistant')}
            </div>
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
      
      {/* Avatar Video Display - Large YouTube/Zoom Style */}
      {enableAvatar && avatarVideo && (
        <div className="avatar-display-section">
          <div className="avatar-video-container">
            <video 
              src={avatarVideo}
              controls
              className="avatar-video-large"
              autoPlay
              loop
            />
            <div className="avatar-info" style={{
              position: 'absolute',
              bottom: '20px',
              left: '20px',
              background: 'rgba(0, 0, 0, 0.7)',
              padding: '10px 20px',
              borderRadius: '8px',
              zIndex: 10
            }}>
              <span>🎬 Avatar Video - Real-time Voice Clone</span>
              <button 
                onClick={() => setAvatarVideo(null)}
                className="btn-close-avatar"
                style={{marginLeft: '10px', padding: '5px 10px'}}
              >
                ✕ Close
              </button>
            </div>
          </div>
        </div>
      )}

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
