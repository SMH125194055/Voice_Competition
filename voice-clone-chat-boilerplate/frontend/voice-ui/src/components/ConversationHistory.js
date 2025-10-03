import React, { useState } from 'react';
import './ConversationHistory.css';

const ConversationHistory = ({ conversations, onDelete }) => {
  const [expandedId, setExpandedId] = useState(null);

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const formatTimestamp = (isoString) => {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const downloadAudio = (audioUrl, filename) => {
    const a = document.createElement('a');
    a.href = audioUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="conversation-history">
      {conversations.map((conv) => (
        <div 
          key={conv.id} 
          className={`conversation-item ${expandedId === conv.id ? 'expanded' : ''}`}
        >
          {/* Header */}
          <div className="conversation-header" onClick={() => toggleExpand(conv.id)}>
            <div className="conversation-info">
              <span className="conversation-icon">💬</span>
              <div className="conversation-text-preview">
                <p className="question-preview">
                  <strong>Q:</strong> {conv.questionText.substring(0, 60)}
                  {conv.questionText.length > 60 ? '...' : ''}
                </p>
                <p className="timestamp">{formatTimestamp(conv.timestamp)}</p>
              </div>
            </div>
            <div className="conversation-actions">
              <button 
                className="expand-button"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(conv.id);
                }}
              >
                {expandedId === conv.id ? '▲' : '▼'}
              </button>
              <button
                className="delete-button"
                onClick={(e) => {
                  e.stopPropagation();
                  if (window.confirm('Delete this conversation?')) {
                    onDelete(conv.id);
                  }
                }}
              >
                🗑️
              </button>
            </div>
          </div>

          {/* Expanded Content */}
          {expandedId === conv.id && (
            <div className="conversation-details">
              {/* Reference Voice */}
              <div className="detail-section">
                <h4>🎤 Reference Voice</h4>
                <div className="audio-section">
                  <audio controls src={conv.referenceAudioUrl} className="detail-audio" />
                  <button
                    className="download-button"
                    onClick={() => downloadAudio(conv.referenceAudioUrl, `reference_${conv.id}.wav`)}
                  >
                    ⬇️ Download
                  </button>
                </div>
              </div>

              {/* Question */}
              <div className="detail-section">
                <h4>❓ Your Question</h4>
                <div className="text-box">
                  <p>{conv.questionText}</p>
                </div>
                <div className="audio-section">
                  <audio controls src={conv.questionAudioUrl} className="detail-audio" />
                  <button
                    className="download-button"
                    onClick={() => downloadAudio(conv.questionAudioUrl, `question_${conv.id}.wav`)}
                  >
                    ⬇️ Download
                  </button>
                </div>
              </div>

              {/* Answer */}
              <div className="detail-section">
                <h4>🤖 AI Response (Cloned Voice)</h4>
                <div className="text-box answer-box">
                  <p>{conv.answerText}</p>
                </div>
                <div className="audio-section">
                  <audio controls src={conv.answerAudioUrl} className="detail-audio" />
                  <button
                    className="download-button"
                    onClick={() => downloadAudio(conv.answerAudioUrl, `answer_${conv.id}.wav`)}
                  >
                    ⬇️ Download
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default ConversationHistory;

