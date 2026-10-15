import React, { useEffect } from 'react';
import { LogOut, X, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function SignoutModal({ isOpen, user, onClose, onConfirm, isSigningOut }) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isSigningOut) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, isSigningOut]);

  if (!isOpen) return null;

  const displayName = user?.display_name || user?.email?.split('@')[0] || 'Executive User';
  const email = user?.email || '';
  const role = user?.role || 'user';

  return (
    <div
      className={`modal-overlay signout-modal-overlay ${isSigningOut ? 'signout-exiting' : ''}`}
      onClick={() => {
        if (!isSigningOut) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="signout-dialog-title"
    >
      <div
        className="signout-modal-container animate-modal-pop"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          type="button"
          className="signout-close-btn"
          onClick={onClose}
          disabled={isSigningOut}
          aria-label="Cancel sign out"
        >
          <X size={18} />
        </button>

        {/* Header Icon */}
        <div className="signout-icon-wrapper">
          <div className="signout-icon-pulse" />
          <div className="signout-icon-circle">
            <LogOut size={26} className="signout-icon" />
          </div>
        </div>

        {/* Title & Description */}
        <h3 id="signout-dialog-title" className="signout-title">
          Confirm Sign Out
        </h3>
        <p className="signout-subtitle">
          Are you sure you want to end your active session on <strong>ITC Insight</strong>?
        </p>

        {/* User Card */}
        {user && (
          <div className="signout-user-card">
            <div className="signout-user-avatar">
              {displayName.slice(0, 2).toUpperCase()}
            </div>
            <div className="signout-user-details">
              <span className="signout-user-name">{displayName}</span>
              <span className="signout-user-email">{email}</span>
            </div>
            <span className={`signout-role-badge ${role === 'admin' ? 'admin' : ''}`}>
              {role === 'admin' ? '🛡️ Admin' : 'Executive'}
            </span>
          </div>
        )}

        {/* Session info note */}
        <div className="signout-info-note">
          <ShieldCheck size={16} className="signout-note-icon" />
          <span>
            Your inquiry history and analysis sessions are securely saved in Google Cloud Firestore and will be waiting when you return.
          </span>
        </div>

        {/* Modal Actions */}
        <div className="signout-actions">
          <button
            type="button"
            className="signout-btn-cancel"
            onClick={onClose}
            disabled={isSigningOut}
          >
            Cancel
          </button>
          <button
            type="button"
            className={`signout-btn-confirm ${isSigningOut ? 'loading' : ''}`}
            onClick={onConfirm}
            disabled={isSigningOut}
          >
            {isSigningOut ? (
              <>
                <span className="signout-spinner" />
                <span>Signing Out...</span>
              </>
            ) : (
              <>
                <LogOut size={16} />
                <span>Yes, Sign Out</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

