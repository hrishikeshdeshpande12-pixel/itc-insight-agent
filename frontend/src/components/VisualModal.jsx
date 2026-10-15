import React, { useEffect } from 'react';

export default function VisualModal({ imageUrl, title, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!imageUrl) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">{title || 'Document Page Source Preview'}</div>
          <button className="modal-close" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>
        <div className="modal-body">
          <img
            src={imageUrl}
            alt={title || 'Document Page Preview'}
            className="modal-image"
          />
        </div>
      </div>
    </div>
  );
}

