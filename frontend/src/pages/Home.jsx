import React, { useState, useEffect, useRef } from 'react';
import Header from '../components/Header';
import ChatMessage from '../components/ChatMessage';
import SuggestedQuestions from '../components/SuggestedQuestions';
import LoadingIndicator from '../components/LoadingIndicator';
import ResourceInspectorModal from '../components/ResourceInspectorModal';
import AuthPage from '../components/AuthPage';
import HistorySidebar from '../components/HistorySidebar';
import AdminPortal from '../components/AdminPortal';
import SignoutModal from '../components/SignoutModal';

import {
  fetchHealth,
  sendChatMessage,
  getStoredUser,
  setStoredUser,
  setAuthToken,
  fetchCurrentUserApi,
  fetchSessionsApi,
  fetchSessionMessagesApi,
  deleteSessionApi,
} from '../services/api';

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [selectedResource, setSelectedResource] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Authentication & History State
  const [user, setUser] = useState(getStoredUser());
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(
    typeof window !== 'undefined' ? window.innerWidth < 1080 : false
  );
  const [sessions, setSessions] = useState([]);
  const [showAdminPortal, setShowAdminPortal] = useState(false);
  const [showSignoutModal, setShowSignoutModal] = useState(false);
  const [isSigningOut, setIsSigningOut] = useState(false);


  // Persistent session identifier across turns
  const sessionIdRef = useRef('itc_sess_' + Math.random().toString(36).substring(2, 11));

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Check backend health & auto-refresh sessions
  useEffect(() => {
    async function checkStatus() {
      const health = await fetchHealth();
      setIsReady(health.vector_store_ready || health.status === 'healthy');
    }
    checkStatus();
    const interval = setInterval(checkStatus, 20000);
    return () => clearInterval(interval);
  }, []);

  // Check stored user profile validity on mount
  useEffect(() => {
    async function verifyUser() {
      if (user) {
        const profile = await fetchCurrentUserApi();
        if (profile) {
          setUser(profile);
          loadUserSessions();
        } else {
          setUser(null);
        }
      }
    }
    verifyUser();
  }, []);

  const loadUserSessions = async () => {
    try {
      const userSessions = await fetchSessionsApi();
      setSessions(userSessions);
    } catch (err) {
      console.error('Could not fetch sessions from Firestore:', err);
    }
  };

  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  const executeInquiry = async (queryText) => {
    const q = queryText.trim();
    if (!q || loading) return;

    setErrorMsg(null);
    setInputQuestion('');
    setMessages((prev) => [...prev, { role: 'user', content: q }]);
    setLoading(true);

    try {
      // Send message with persistent session ID to maintain conversation context
      const response = await sendChatMessage(q, sessionIdRef.current);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          citations: response.citations,
          visual_context_used: response.visual_context_used,
          source_type: response.source_type,
          related_images: response.related_images || [],
        },
      ]);

      // If user is logged in, refresh sessions in background so the history is up-to-date
      if (user) {
        setTimeout(loadUserSessions, 1200);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setErrorMsg(err.message || 'Unable to connect to intelligence engine.');
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'An error occurred while connecting to the intelligence engine. Please ensure the backend server is running.',
          citations: [],
          visual_context_used: false,
          source_type: 'none',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    executeInquiry(inputQuestion);
  };

  const handleSelectSuggested = (suggestedText) => {
    setInputQuestion(suggestedText);
    inputRef.current?.focus();
  };

  const handleFollowUpClick = (followUpText) => {
    executeInquiry(followUpText);
  };

  const handleOpenResource = (citation) => {
    setSelectedResource(citation);
  };

  const handleCloseResource = () => {
    setSelectedResource(null);
  };

  const handleNewInquiry = () => {
    setMessages([]);
    setInputQuestion('');
    setErrorMsg(null);
    sessionIdRef.current = 'itc_sess_' + Math.random().toString(36).substring(2, 11);
    if (typeof window !== 'undefined' && window.innerWidth < 900) {
      setIsSidebarCollapsed(true);
    }
  };

  const handleSelectSession = async (sessionId) => {
    sessionIdRef.current = sessionId;
    setErrorMsg(null);
    setLoading(true);
    if (typeof window !== 'undefined' && window.innerWidth < 900) {
      setIsSidebarCollapsed(true);
    }
    try {
      const sessionMessages = await fetchSessionMessagesApi(sessionId);
      setMessages(sessionMessages || []);
    } catch (err) {
      console.error('Could not load session from Firestore:', err);
      setErrorMsg('Failed to load conversation history from Firestore.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await deleteSessionApi(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
      if (sessionIdRef.current === sessionId) {
        handleNewInquiry();
      }
    } catch (err) {
      console.error('Error deleting session:', err);
    }
  };

  const handleAuthSuccess = (authenticatedUser) => {
    setUser(authenticatedUser);
    loadUserSessions();
  };

  const handleRequestLogout = () => {
    setShowSignoutModal(true);
  };

  const handleConfirmLogout = () => {
    setIsSigningOut(true);
    // Smooth transition delay for exit animation
    setTimeout(() => {
      setAuthToken(null);
      setStoredUser(null);
      setUser(null);
      setSessions([]);
      handleNewInquiry();
      setIsSigningOut(false);
      setShowSignoutModal(false);
    }, 450);
  };

  // Enforce authentication gate: guest users cannot view or send chats
  if (!user) {
    return <AuthPage onAuthSuccess={handleAuthSuccess} />;
  }

  return (
    <div className="app-shell">
      {/* Permanent Left Sidebar for Inquiry History */}
      <HistorySidebar
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        sessions={sessions}
        activeSessionId={sessionIdRef.current}
        onSelectSession={handleSelectSession}
        onDeleteSession={handleDeleteSession}
        onNewInquiry={handleNewInquiry}
        user={user}
        onLogout={handleRequestLogout}
      />

      {/* Mobile Drawer Backdrop Overlay */}
      {!isSidebarCollapsed && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={() => setIsSidebarCollapsed(true)}
          aria-label="Close conversation history drawer"
        />
      )}

      {/* Main Content Area */}
      <div className={`app-main-pane ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Header
          isReady={isReady}
          onNewInquiry={handleNewInquiry}
          hasMessages={messages.length > 0}
          isSidebarCollapsed={isSidebarCollapsed}
          onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          user={user}
          onOpenAuth={() => {}}
          onLogout={handleRequestLogout}
          onOpenAdmin={() => setShowAdminPortal(true)}
        />


      <main className="main-content">
        {messages.length === 0 ? (
          <section className="hero-section modern-hero-section">
            <div className="hero-glow-backdrop" aria-hidden="true" />

            <div className="hero-badge-pill">
              <span className="sparkle-icon">✨</span>
              <span>ITC Limited Official Intelligence Platform &bull; Cloud Unified</span>
            </div>

            <div className="hero-logo-banner">
              <img
                src="/itc-logo-clean.webp"
                alt="ITC Limited Corporate Logo"
                className="hero-logo-img animate-float"
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = '/itc-logo.webp';
                }}
              />
            </div>

            <h2 className="hero-title">
              Enterprise Insight for <span className="highlight">ITC Limited</span>
            </h2>

            <p className="hero-subtitle">
              Synthesizing corporate strategy, FMCG growth vectors, multi-capital value creation, corporate governance, and ESG leadership with Firestore Cloud persistence.
            </p>

            <div className="search-container modern-search-container">
              <form onSubmit={handleSubmit} className="search-box-wrapper modern-search-box">
                <div className="search-icon" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                </div>
                <input
                  ref={inputRef}
                  type="text"
                  className="search-input"
                  placeholder="Ask about ITC Next strategy, FMCG platforms, value creation, governance..."
                  value={inputQuestion}
                  onChange={(e) => setInputQuestion(e.target.value)}
                  disabled={loading}
                />
                {inputQuestion.trim() && (
                  <button
                    type="button"
                    className="clear-input-btn"
                    onClick={() => setInputQuestion('')}
                    title="Clear input"
                  >
                    &times;
                  </button>
                )}
                <button
                  type="submit"
                  className="search-button modern-submit-btn"
                  disabled={!inputQuestion.trim() || loading}
                >
                  <span>Inquire</span>
                  <span aria-hidden="true" className="arrow">&rarr;</span>
                </button>
              </form>
            </div>

            <SuggestedQuestions onSelectQuestion={handleSelectSuggested} />
          </section>
        ) : (
          <div className="chat-stream modern-chat-stream">
            <div className="messages-scroll-area">
              {messages.map((msg, idx) => (
                <ChatMessage
                  key={idx}
                  message={msg}
                  onSelectResource={handleOpenResource}
                  onPreviewImage={(url, title) => handleOpenResource({ image_url: url, title, source_type: 'document' })}
                  onFollowUp={idx === messages.length - 1 && !loading ? handleFollowUpClick : null}
                />
              ))}

              {loading && <LoadingIndicator />}
              {errorMsg && (
                <div className="error-toast-banner">
                  <span>⚠️ {errorMsg}</span>
                </div>
              )}
              <div ref={messagesEndRef} className="messages-bottom-anchor" />
            </div>

            <div className="docked-search-container modern-docked-container">
              <form onSubmit={handleSubmit} className="search-box-wrapper modern-docked-box">
                <div className="search-icon" aria-hidden="true">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                </div>
                <input
                  ref={inputRef}
                  type="text"
                  className="search-input"
                  placeholder="Ask a strategic follow-up or explore another ITC domain..."
                  value={inputQuestion}
                  onChange={(e) => setInputQuestion(e.target.value)}
                  disabled={loading}
                />
                {inputQuestion.trim() && (
                  <button
                    type="button"
                    className="clear-input-btn"
                    onClick={() => setInputQuestion('')}
                    title="Clear input"
                  >
                    &times;
                  </button>
                )}
                <button
                  type="submit"
                  className="search-button modern-submit-btn"
                  disabled={!inputQuestion.trim() || loading}
                >
                  <span>Inquire</span>
                  <span aria-hidden="true" className="arrow">&rarr;</span>
                </button>
              </form>
              <div className="docked-hint-text">
                Press Enter to inquire &bull; Stored in Google Cloud Firestore &bull; Grounded in official ITC records
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="app-footer modern-footer">
        <div className="footer-left">
          <span className="footer-brand">ITC Limited</span> &bull; ITC INSIGHT &bull; Market Intelligence &bull; Strategy &bull; Governance
        </div>
        <div className="footer-right">
          Grounded strictly in official ITC Annual Reports, CMD Analyst Decks &amp; Sustainability Filings
        </div>
      </footer>
      </div>

      {selectedResource && (
        <ResourceInspectorModal
          resource={selectedResource}
          onClose={handleCloseResource}
        />
      )}

      {showAdminPortal && (
        <AdminPortal
          user={user}
          onClose={() => setShowAdminPortal(false)}
        />
      )}

      <SignoutModal
        isOpen={showSignoutModal}
        user={user}
        isSigningOut={isSigningOut}
        onClose={() => {
          if (!isSigningOut) setShowSignoutModal(false);
        }}
        onConfirm={handleConfirmLogout}
      />
    </div>
  );
}


