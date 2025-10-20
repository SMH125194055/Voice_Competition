import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import ConversationHistory from './components/ConversationHistory';
import AudioRecorder from './components/AudioRecorder';
import ReferenceVoiceManager from './components/ReferenceVoiceManager';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  // State management
  const [referenceAudio, setReferenceAudio] = useState(null);
  const [referenceAudioUrl, setReferenceAudioUrl] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState('');
  const [error, setError] = useState(null);

  // Load conversations from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('voiceConversations');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setConversations(parsed);
      } catch (e) {
        console.error('Failed to load conversations:', e);
      }
    }
  }, []);

  // Save conversations to localStorage whenever they change
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem('voiceConversations', JSON.stringify(conversations));
    }
  }, [conversations]);

  // Handle reference audio upload/recording
  const handleReferenceAudioChange = (audioBlob, audioUrl) => {
    setReferenceAudio(audioBlob);
    setReferenceAudioUrl(audioUrl);
    setError(null);
  };

  // Handle user question recording
  const handleQuestionRecorded = async (audioBlob, audioUrl) => {
    if (!referenceAudio) {
      setError('Please record or upload a reference voice first!');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setCurrentStep('Preparing audio...');

    try {
      // Create FormData for the full pipeline
      const formData = new FormData();
      formData.append('audio', audioBlob, 'question.wav');

      // Step 1: Transcribe the question
      setCurrentStep('🎤 Transcribing your question...');
      const transcribeResponse = await axios.post(
        `${API_BASE_URL}/transcribe`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );
      const questionText = transcribeResponse.data.text;
      console.log('Transcribed:', questionText);

      // Step 2: Get LLM response
      setCurrentStep('🤖 Getting AI response...');
      const chatResponse = await axios.post(
        `${API_BASE_URL}/chat`,
        { message: questionText },
        {
          headers: { 'Content-Type': 'application/json' }
        }
      );
      const answerText = chatResponse.data.reply;
      console.log('AI replied:', answerText);

      // Step 3: Generate cloned voice with user's reference audio
      setCurrentStep('🔊 Generating voice (this may take 5-8 minutes on CPU)...');
      
      // Create FormData to send both text and reference audio
      const speakFormData = new FormData();
      speakFormData.append('text', answerText);
      if (referenceAudio) {
        speakFormData.append('reference_audio', referenceAudio, 'reference.wav');
      }
      
      const speakResponse = await axios.post(
        `${API_BASE_URL}/speak`,
        speakFormData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          responseType: 'blob'
        }
      );

      // Create audio URL for the generated response
      const answerAudioBlob = speakResponse.data;
      const answerAudioUrl = URL.createObjectURL(answerAudioBlob);

      // Save conversation
      const newConversation = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        referenceAudioUrl: referenceAudioUrl,
        questionAudioUrl: audioUrl,
        questionText: questionText,
        answerText: answerText,
        answerAudioUrl: answerAudioUrl,
        answerAudioBlob: answerAudioBlob
      };

      setConversations(prev => [newConversation, ...prev]);
      setCurrentStep('✅ Complete!');
      
      // Clear step after 2 seconds
      setTimeout(() => setCurrentStep(''), 2000);

    } catch (err) {
      console.error('Error processing voice chat:', err);
      setError(
        err.response?.data?.detail || 
        err.message || 
        'Failed to process voice chat. Please try again.'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  // Clear all conversations
  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear all conversation history?')) {
      setConversations([]);
      localStorage.removeItem('voiceConversations');
    }
  };

  // Delete single conversation
  const handleDeleteConversation = (id) => {
    setConversations(prev => prev.filter(conv => conv.id !== id));
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎙️ Voice Clone Chat</h1>
        <p className="subtitle">Talk to AI and hear it respond in your voice!</p>
      </header>

      <main className="App-main">
        {/* Error Display */}
        {error && (
          <div className="error-banner">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {/* Processing Status */}
        {isProcessing && (
          <div className="processing-banner">
            <div className="spinner"></div>
            <span>{currentStep}</span>
          </div>
        )}

        {/* Step 1: Reference Voice */}
        <section className="section">
          <h2>📁 Step 1: Set Your Reference Voice</h2>
          <p className="section-description">
            Record or upload 3-10 seconds of your voice. This will be used to clone your voice.
          </p>
          <ReferenceVoiceManager
            onAudioChange={handleReferenceAudioChange}
            currentAudioUrl={referenceAudioUrl}
            disabled={isProcessing}
          />
        </section>

        {/* Step 2: Ask Question */}
        <section className="section">
          <h2>❓ Step 2: Ask Your Question</h2>
          <p className="section-description">
            Record your question. The AI will respond in your cloned voice.
          </p>
          <AudioRecorder
            onRecordingComplete={handleQuestionRecorded}
            disabled={!referenceAudio || isProcessing}
            buttonText="Record Question"
          />
          {!referenceAudio && (
            <p className="warning-text">
              ⚠️ Please set a reference voice first
            </p>
          )}
        </section>

        {/* Step 3: Conversation History */}
        <section className="section">
          <div className="section-header">
            <h2>💬 Conversation History ({conversations.length})</h2>
            {conversations.length > 0 && (
              <button 
                className="clear-button"
                onClick={handleClearHistory}
              >
                🗑️ Clear All
              </button>
            )}
          </div>
          
          {conversations.length === 0 ? (
            <div className="empty-state">
              <p>No conversations yet. Start by recording your first question!</p>
            </div>
          ) : (
            <ConversationHistory
              conversations={conversations}
              onDelete={handleDeleteConversation}
            />
          )}
        </section>
      </main>

      <footer className="App-footer">
        <p>Built with ❤️ using Whisper, GPT-3.5, and ChatterBox</p>
        <p className="footer-note">
          💡 Tip: First generation takes 5-8 minutes on CPU, ~30-60 seconds on GPU
        </p>
      </footer>
    </div>
  );
}

export default App;
