import React from 'react';

export default function LoadingIndicator() {
  return (
    <div className="thinking-indicator-card animate-reveal" role="status" aria-live="polite">
      <div className="thinking-indicator-content">
        <div className="thinking-orbit-badge" aria-hidden="true">
          <div className="thinking-orbit-ring" />
          <div className="thinking-orbit-core" />
        </div>

        <div className="thinking-title-row">
          <span className="thinking-title-text">Thinking</span>
          <div className="thinking-dots" aria-hidden="true">
            <span className="thinking-dot dot-1" />
            <span className="thinking-dot dot-2" />
            <span className="thinking-dot dot-3" />
          </div>
        </div>
      </div>

      <div className="thinking-progress-track" aria-hidden="true">
        <div className="thinking-progress-shimmer" />
      </div>
    </div>
  );
}
