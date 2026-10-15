import React from 'react';

export default function SourceCard({ citation, onSelectResource, onPreviewImage }) {
  const isDocument = citation.source_type === 'document';
  const matchPercent = citation.score ? Math.round(citation.score * 100) : null;

  const handleCardClick = (e) => {
    // If the user clicked an explicit external hyperlink, don't hijack
    if (e.target.tagName === 'A') return;
    if (onSelectResource) {
      onSelectResource(citation);
    } else if (onPreviewImage && citation.image_url) {
      onPreviewImage(citation.image_url, `${citation.title} (Page ${citation.page_number})`);
    }
  };

  return (
    <div
      className="source-card modern-source-card"
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handleCardClick(e);
        }
      }}
    >
      <div className="source-card-top">
        <div className="source-card-badges">
          <span className={`source-type-pill ${isDocument ? 'doc' : 'web'}`}>
            {isDocument ? '📄 Document Evidence' : '🌐 Web Grounding'}
          </span>
          {isDocument && citation.page_number && (
            <span className="source-page-pill">Page {citation.page_number}</span>
          )}
          {matchPercent && (
            <span className="source-score-pill">{matchPercent}% Match</span>
          )}
        </div>
      </div>

      <div className="source-card-title-row">
        <h4 className="source-card-title" title={citation.title}>
          {citation.title}
        </h4>
      </div>

      {citation.snippet && (
        <p className="source-card-snippet">
          {citation.snippet}
        </p>
      )}

      <div className="source-card-footer">
        {isDocument ? (
          <button
            type="button"
            className="source-inspect-btn"
            onClick={(e) => {
              e.stopPropagation();
              handleCardClick(e);
            }}
          >
            <span>Inspect Resource &amp; Page Scan</span>
            <span className="arrow-icon">&rarr;</span>
          </button>
        ) : citation.url ? (
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="source-inspect-btn web-link"
            onClick={(e) => e.stopPropagation()}
          >
            <span>Visit Web Reference</span>
            <span className="arrow-icon">&#8599;</span>
          </a>
        ) : (
          <button
            type="button"
            className="source-inspect-btn"
            onClick={(e) => {
              e.stopPropagation();
              handleCardClick(e);
            }}
          >
            <span>View Excerpt</span>
            <span className="arrow-icon">&rarr;</span>
          </button>
        )}
      </div>
    </div>
  );
}
