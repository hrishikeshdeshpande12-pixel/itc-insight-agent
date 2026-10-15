import React, { useState, useEffect } from 'react';

export default function ResourceInspectorModal({ resource, onClose }) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [imgLoading, setImgLoading] = useState(true);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!resource) return null;

  const isDocument = resource.source_type === 'document' || !resource.url;
  const pageImageSrc = resource.image_url || (isDocument && resource.title && resource.page_number
    ? `/api/documents/page-image?document=${encodeURIComponent(resource.title)}&page=${resource.page_number}`
    : null);

  const handleZoomIn = () => setZoomLevel((z) => Math.min(z + 0.25, 2.5));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(z - 0.25, 0.75));
  const handleResetZoom = () => setZoomLevel(1);

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="inspector-modal-container animate-modal-pop" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="inspector-header">
          <div className="inspector-title-area">
            <div className="inspector-meta-row">
              <span className="inspector-type-tag doc">
                📸 Official Document Visual Scan
              </span>
              {resource.page_number && (
                <span className="inspector-page-tag">Page {resource.page_number}</span>
              )}
            </div>
            <h3 className="inspector-document-title">
              {resource.title || 'Official Document Strategy Architecture & Diagram'}
            </h3>
          </div>

          <div className="inspector-header-actions">
            {pageImageSrc && (
              <a
                href={pageImageSrc}
                target="_blank"
                rel="noopener noreferrer"
                className="inspector-action-btn"
                title="Open high-res scan in new tab"
              >
                ↗ Full Image
              </a>
            )}
            <button
              type="button"
              className="inspector-close-btn"
              onClick={onClose}
              aria-label="Close inspector"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Modal Body: Strictly Page Visual Scan */}
        <div className="inspector-body">
          <div className="inspector-visual-view">
            {pageImageSrc ? (
              <>
                <div className="zoom-controls-toolbar">
                  <span className="zoom-indicator">Zoom: {Math.round(zoomLevel * 100)}%</span>
                  <div className="zoom-btn-group">
                    <button type="button" onClick={handleZoomOut} className="zoom-btn" title="Zoom out">-</button>
                    <button type="button" onClick={handleResetZoom} className="zoom-btn" title="Reset zoom">Reset</button>
                    <button type="button" onClick={handleZoomIn} className="zoom-btn" title="Zoom in">+</button>
                  </div>
                </div>

                <div className="image-viewport">
                  {imgLoading && (
                    <div className="image-loading-state">
                      <div className="spinner-ring" />
                      <span>Rendering high-resolution page scan...</span>
                    </div>
                  )}
                  {imgError ? (
                    <div className="image-error-fallback">
                      <p>High-resolution scan could not be loaded.</p>
                    </div>
                  ) : (
                    <img
                      src={pageImageSrc}
                      alt={resource.title || 'Document Visual Scan'}
                      className="rendered-page-image"
                      style={{ transform: `scale(${zoomLevel})` }}
                      onLoad={() => setImgLoading(false)}
                      onError={() => {
                        setImgLoading(false);
                        setImgError(true);
                      }}
                    />
                  )}
                </div>
              </>
            ) : (
              <div className="no-image-notice">
                <p>Visual page scan not available for this record.</p>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="inspector-footer">
          <div className="footer-provenance">
            <strong>Provenance:</strong> ITC Limited Official Annual Report & Accounts &bull; Verified High-Resolution Visual Architecture
          </div>
          <button type="button" className="footer-close-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
