import React, { useState } from 'react';
import { loginApi, registerApi } from '../services/api';

export default function AuthPage({ onAuthSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [pendingRegistration, setPendingRegistration] = useState(null);

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
        if (result.status === 'pending') {
          setPendingRegistration({
            email: cleanEmail,
            displayName,
            message: result.message || 'Administrator approval is required before you can log in.',
          });
          setLoading(false);
          return;
        }
      } else {
        result = await loginApi(cleanEmail, password);
      }
      if (onAuthSuccess && result.user) {
        onAuthSuccess(result.user);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page-screen animate-fade-in">
      <div className="auth-page-backdrop" aria-hidden="true" />

      <div className="auth-page-card animate-scale-up">
        {/* Brand Header */}
        <div className="auth-page-brand">
          <div className="auth-page-logo-container">
            <img
              src="/itc-logo-clean.webp"
              alt="ITC Limited Corporate Logo"
              className="auth-page-logo-img"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = '/itc-logo.webp';
              }}
            />
          </div>
          <div className="auth-page-brand-text">
            <h1 className="auth-page-title">ITC INSIGHT</h1>
            <span className="auth-page-badge">Enterprise Intelligence</span>
          </div>
          <p className="auth-page-subtitle">
            Executive Strategy, FMCG Growth Vectors &amp; Governance Platform
          </p>
        </div>

        {/* Pending Registration Approval Screen */}
        {pendingRegistration ? (
          <div className="auth-pending-screen animate-fade-in" style={{ padding: '16px 0', textAlign: 'center' }}>
            <div style={{
              width: '64px',
              height: '64px',
              margin: '0 auto 16px',
              borderRadius: '50%',
              background: '#FEF3C7',
              color: '#D97706',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '30px'
            }}>
              📩
            </div>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#0F172A', margin: '0 0 8px' }}>
              Registration Request Submitted
            </h2>
            <div style={{
              display: 'inline-block',
              padding: '4px 12px',
              borderRadius: '9999px',
              background: '#EFF6FF',
              color: '#2563EB',
              fontSize: '12px',
              fontWeight: '600',
              marginBottom: '16px'
            }}>
              ⏳ Pending Administrator Authorization
            </div>
            <p style={{ fontSize: '13px', lineHeight: '1.6', color: '#475569', margin: '0 0 16px', padding: '0 8px' }}>
              Your account request for <strong>{pendingRegistration.email}</strong> has been registered. An email notification has been dispatched to the administrator:
            </p>
            <div style={{
              background: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '12px 16px',
              marginBottom: '20px',
              fontSize: '13px',
              color: '#0F172A',
              fontWeight: '600',
              wordBreak: 'break-all'
            }}>
              🛡️ hrishikeshdeshpande23@gmail.com
            </div>
            <p style={{ fontSize: '12px', color: '#64748B', margin: '0 0 24px' }}>
              Once your request is authorized in the Admin Portal, you will be able to log in with your credentials.
            </p>
            <button
              type="button"
              className="auth-submit-btn"
              onClick={() => {
                setPendingRegistration(null);
                setIsRegister(false);
                setPassword('');
              }}
            >
              Return to Sign In
            </button>
          </div>
        ) : (
          <>
            {/* Tab Switcher */}
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

            {/* Auth Form */}
            <form onSubmit={handleSubmit} className="auth-form">
              {isRegister && (
                <div className="auth-field-group">
                  <label className="auth-label" htmlFor="page-auth-name">
                    Full Name
                  </label>
                  <input
                    id="page-auth-name"
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
                <label className="auth-label" htmlFor="page-auth-email">
                  Official ITC Email (@itc.in)
                </label>
                <input
                  id="page-auth-email"
                  type="email"
                  className="auth-input"
                  placeholder="e.g. executive@itc.in"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <span style={{ fontSize: '11px', color: '#64748B', marginTop: '4px', display: 'block' }}>
                  🔒 Official ITC Limited domain access only (@itc.in)
                </span>
              </div>

              <div className="auth-field-group">
                <label className="auth-label" htmlFor="page-auth-password">
                  Password
                </label>
                <input
                  id="page-auth-password"
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
                  'Submit Registration Request'
                ) : (
                  'Sign In to Workspace'
                )}
              </button>
            </form>

            {/* Security & Cloud Assurance Footer */}
            <div className="auth-page-footer">
              <div className="auth-cloud-pill">
                <span className="gcp-dot" />
                <span>Google Cloud Firestore Protected &bull; Bcrypt Encrypted</span>
              </div>
              <p className="auth-page-disclaimer">
                Access restricted to authorized personnel. New accounts require administrator approval.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
