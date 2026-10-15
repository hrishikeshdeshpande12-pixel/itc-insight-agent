import React, { useState } from 'react';

export default function Header({
  isReady,
  onNewInquiry,
  hasMessages,
  isSidebarCollapsed,
  onToggleSidebar,
  user,
  onOpenAuth,
  onLogout,
  onOpenAdmin,
}) {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const isAdmin = user && (
    user.role === 'admin' ||
    user.email === 'hrishikeshdeshpande23@gmail.com' ||
    user.email === 'hrishikesh@itc.in'
  );

  const getInitials = (name, email) => {
    if (name) {
      const parts = name.trim().split(' ');
      if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
      return name.slice(0, 2).toUpperCase();
    }
    if (email) return email.slice(0, 2).toUpperCase();
    return 'U';
  };

  return (
    <header className="app-header modern-header">
      <div className="brand-wrapper">
        {/* Sidebar Toggle when collapsed */}
        {isSidebarCollapsed && (
          <button
            type="button"
            className="sidebar-expand-toggle-btn"
            onClick={onToggleSidebar}
            title="Open History Sidebar"
            aria-label="Open History Sidebar"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
            <span className="sidebar-expand-label">History</span>
          </button>
        )}

        <div className="brand-logo-container" onClick={onNewInquiry} role="button" tabIndex={0} title="Return to ITC Insight Home">
          <img
            src="/itc-logo-clean.webp"
            alt="ITC Limited Official Logo"
            className="brand-logo-img"
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = '/itc-logo.webp';
            }}
          />
        </div>
        <div className="brand-divider" aria-hidden="true" />
        <div className="brand-text">
          <div className="brand-title-row">
            <h1 className="brand-heading">ITC INSIGHT</h1>
            <span className="brand-badge-pill">Enterprise Intelligence</span>
          </div>
          <div className="tagline">Market Intelligence &bull; Strategy &bull; Governance</div>
        </div>
      </div>

      <div className="header-right-actions">
        <div className="header-status-pill">
          <span className={`status-pulse ${isReady ? 'online' : 'connecting'}`} aria-hidden="true">
            <span className="status-ping" />
            <span className="status-core" />
          </span>
          <span className="status-text">{isReady ? 'Engine Online' : 'Connecting...'}</span>
        </div>

        {hasMessages && onNewInquiry && (
          <button
            type="button"
            className="new-inquiry-header-btn"
            onClick={onNewInquiry}
            title="Start a new strategic inquiry session"
          >
            <span className="btn-icon">+</span>
            <span className="new-inquiry-label">New Inquiry</span>
          </button>
        )}

        {/* Administrator Portal Button */}
        {isAdmin && onOpenAdmin && (
          <button
            type="button"
            className="admin-portal-header-btn"
            onClick={onOpenAdmin}
            title="Open Administrator Governance & Approval Portal"
            style={{
              background: '#0F172A',
              color: '#FCD34D',
              border: '1px solid #D97706',
              borderRadius: '8px',
              padding: '7px 14px',
              fontSize: '12px',
              fontWeight: '700',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 2px 4px rgba(217, 119, 6, 0.2)'
            }}
          >
            <span className="admin-btn-icon">🛡️</span>
            <span className="admin-btn-label">Admin Portal</span>
          </button>
        )}

        {/* User Account Button & Dropdown */}
        {user ? (
          <div className="user-profile-wrapper">
            <button
              type="button"
              className="user-profile-btn"
              onClick={() => setShowUserMenu(!showUserMenu)}
              title={`Logged in as ${user.display_name || user.email}`}
            >
              <span className="user-avatar-circle">
                {getInitials(user.display_name, user.email)}
              </span>
              <span className="user-name-label">{user.display_name || user.email.split('@')[0]}</span>
              <span className="dropdown-caret">&darr;</span>
            </button>

            {showUserMenu && (
              <div className="user-dropdown-menu animate-scale-up" onClick={() => setShowUserMenu(false)}>
                <div className="user-dropdown-header">
                  <div className="dropdown-user-name">{user.display_name || 'ITC Executive'}</div>
                  <div className="dropdown-user-email">{user.email}</div>
                  <span className="dropdown-cloud-tag">☁️ GCP Firestore Synced</span>
                </div>
                <div className="user-dropdown-divider" />
                {isAdmin && onOpenAdmin && (
                  <button
                    type="button"
                    className="dropdown-item"
                    style={{ color: '#D97706', fontWeight: '600' }}
                    onClick={() => {
                      setShowUserMenu(false);
                      onOpenAdmin();
                    }}
                  >
                    <span>🛡️ Admin Portal</span>
                  </button>
                )}
                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => {
                    setShowUserMenu(false);
                    if (isSidebarCollapsed) onToggleSidebar();
                  }}
                >
                  <span>📂 My Inquiries</span>
                </button>
                <button
                  type="button"
                  className="dropdown-item logout"
                  onClick={() => {
                    setShowUserMenu(false);
                    onLogout();
                  }}
                >
                  <span>🚪 Sign Out</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            className="header-signin-btn"
            onClick={onOpenAuth}
            title="Sign in or register to persist chat history"
          >
            <span className="signin-icon">👤</span>
            <span>Sign In / Register</span>
          </button>
        )}
      </div>
    </header>
  );
}
