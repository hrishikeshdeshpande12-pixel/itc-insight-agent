import React, { useState } from 'react';
import { loginApi, registerApi } from '../services/api';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setLoading(true);

    const cleanEmail = (email || '').trim().toLowerCase();
    const isAdmin = cleanEmail === 'hrishikeshdeshpande23@gmail.com' || cleanEmail === 'hrishikesh@itc.in';
    if (!cleanEmail.endsWith('@itc.in') && !isAdmin) {
      setErrorMsg('Access restricted to official ITC personnel. Only corporate @itc.in email addresses are permitted.');
      setLoading(false);
      return;
    }

    try {
      let result;
      if (isRegister) {
        result = await registerApi(cleanEmail, password, displayName);
      } else {
        result = await loginApi(cleanEmail, password);
      }
      if (onAuthSuccess) {
        onAuthSuccess(result.user);
      }
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-modal-backdrop animate-fade-in" onClick={onClose} role="dialog" aria-modal="true">
      <div className="auth-modal-card animate-scale-up" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="auth-modal-close" onClick={onClose} aria-label="Close modal">
          &times;
        </button>

        <div className="auth-modal-header">
          <div className="auth-logo-badge">
            <img
              src="/itc-logo-clean.webp"
              alt="ITC Logo"
              className="auth-logo-img"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = '/itc-logo.webp';
              }}
            />
          </div>
          <h2 className="auth-title">ITC Enterprise Access</h2>
          <p className="auth-subtitle">
            {isRegister
              ? 'Create your corporate account to persist and synchronize strategic inquiry history across devices.'
              : 'Sign in to access your stored inquiries and executive strategy briefings.'}
          </p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${!isRegister ? 'active' : ''}`}
            onClick={() => {
              setIsRegister(false);
              setErrorMsg(null);
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab ${isRegister ? 'active' : ''}`}
            onClick={() => {
              setIsRegister(true);
              setErrorMsg(null);
            }}
          >
            Create Account
          </button>
        </div>

        {errorMsg && (
          <div className="auth-error-banner animate-shake">
            <span className="error-icon">⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          {isRegister && (
            <div className="auth-field-group">
              <label className="auth-label" htmlFor="auth-name">Full Name</label>
              <input
                id="auth-name"
                type="text"
                className="auth-input"
                placeholder="e.g. Hrishikesh Deshpande"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
            </div>
          )}

          <div className="auth-field-group">
            <label className="auth-label" htmlFor="auth-email">Corporate Email</label>
            <input
              id="auth-email"
              type="email"
              className="auth-input"
              placeholder="e.g. user@itc.in"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="auth-field-group">
            <label className="auth-label" htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              className="auth-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? (
              <span className="auth-spinner-row">
                <span className="auth-spinner" />
                <span>Authenticating with Firestore...</span>
              </span>
            ) : isRegister ? (
              'Create Account & Sign In'
            ) : (
              'Sign In to ITC Insight'
            )}
          </button>
        </form>

        <div className="auth-footer">
          <span className="auth-footer-tag">🔒 GCP Firestore Cloud Security &bull; End-to-End Partitioned History</span>
        </div>
      </div>
    </div>
  );
}

