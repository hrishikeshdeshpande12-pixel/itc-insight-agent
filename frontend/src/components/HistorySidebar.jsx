import React from 'react';

function formatTimestamp(isoStr) {
  if (!isoStr) return '';
  try {
    const date = new Date(isoStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch {
    return '';
  }
}

export default function HistorySidebar({
  isCollapsed,
  onToggleCollapse,
  sessions,
  activeSessionId,
  onSelectSession,
  onDeleteSession,
  onNewInquiry,
  user,
  onLogout,
}) {
  return (
    <aside className={`app-sidebar ${isCollapsed ? 'collapsed' : ''}`} aria-label="Conversation History">
      <div className="sidebar-inner">
        {/* Sidebar Header */}
        <div className="sidebar-top-bar">
          <div className="sidebar-title-group">
            <span className="sidebar-title-icon">📂</span>
            <span className="sidebar-heading">Inquiries</span>
            {user && sessions.length > 0 && (
              <span className="sidebar-count-badge">{sessions.length}</span>
            )}
          </div>
          <button
            type="button"
            className="sidebar-collapse-btn"
            onClick={onToggleCollapse}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
              <path d="M15 9l-3 3 3 3" />
            </svg>
          </button>
        </div>

        {/* New Inquiry Action Button */}
        <div className="sidebar-action-container">
          <button
            type="button"
            className="sidebar-new-inquiry-btn"
            onClick={onNewInquiry}
            title="Start a new strategic inquiry session"
          >
            <span className="new-btn-icon">+</span>
            <span>New Inquiry</span>
          </button>
        </div>

        {/* Scrollable Sessions List */}
        <div className="sidebar-sessions-scroll">
          {sessions.length === 0 ? (
            <div className="sidebar-empty-state">
              <span className="empty-state-icon">💬</span>
              <p className="empty-state-title">No prior inquiries</p>
              <span className="empty-state-sub">
                Your questions and briefings will appear here automatically.
              </span>
            </div>
          ) : (
            <div className="session-items-wrapper">
              <div className="session-group-header">Recent Sessions</div>
              {sessions.map((sess) => {
                const isActive = sess.session_id === activeSessionId;
                return (
                  <div
                    key={sess.session_id}
                    className={`sidebar-session-row ${isActive ? 'active' : ''}`}
                    onClick={() => onSelectSession(sess.session_id)}
                    role="button"
                    tabIndex={0}
                    title={sess.title}
                  >
                    <div className="session-row-main">
                      <span className="session-row-icon">📑</span>
                      <div className="session-row-details">
                        <div className="session-row-title">{sess.title || 'ITC Inquiry'}</div>
                        <div className="session-row-meta">
                          <span>{formatTimestamp(sess.updated_at || sess.created_at)}</span>
                          {sess.message_count > 0 && (
                            <span className="session-count-tag">{sess.message_count} msgs</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <button
                      type="button"
                      className="session-delete-icon-btn"
                      title="Delete conversation from Firestore"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Delete this conversation history from Firestore?')) {
                          onDeleteSession(sess.session_id);
                        }
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Sidebar Footer with Live Cloud Indicator & User Profile */}
        <div className="sidebar-footer">
          <div className="firestore-status-indicator">
            <span className="live-dot" />
            <span className="indicator-text">GCP Firestore &bull; Synced</span>
          </div>

          {user && (
            <div className="sidebar-user-row">
              <div className="sidebar-user-info" title={user.email}>
                <span className="sidebar-user-avatar">
                  {(user.display_name || user.email || 'U').slice(0, 2).toUpperCase()}
                </span>
                <span className="sidebar-user-name">
                  {user.display_name || user.email.split('@')[0]}
                </span>
              </div>
              <button
                type="button"
                className="sidebar-logout-btn"
                onClick={onLogout}
                title="Sign out and return to login page"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

