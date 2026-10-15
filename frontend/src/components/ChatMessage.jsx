import React, { useState } from 'react';

function stripSourceCitations(text) {
  if (!text) return '';
  return text
    // Remove bracketed or parenthesized references containing .pdf, source:, or doc:
    .replace(/\[\s*(?:source|sources|ref|reference|doc|document)?\s*:?[^\]]*?\.pdf[^\]]*?\]/gi, '')
    .replace(/\(\s*(?:source|sources|ref|reference|doc|document)?\s*:?[^)]*?\.pdf[^)]*?\)/gi, '')
    .replace(/\[\s*(?:source|sources|ref|reference)\s*:[^\]]*?\]/gi, '')
    .replace(/\(\s*(?:source|sources|ref|reference)\s*:[^)]*?\)/gi, '')
    // Remove standalone lines starting with Source: or **Source:** or *Source:*
    .replace(/^ *(?:\*{0,2})Sources?(?:\*{0,2}) *:.*$/gim, '')
    // Remove inline "Source: ... .pdf..." or "Source: ... Page X" or "cmd_presentation.pdf, Page 8"
    .replace(/\bSources? *:\s*[\w\-\.\/\s]+\.pdf(?:\s*,?\s*(?:page|pg|slide)\s*\d+)?/gi, '')
    .replace(/\b[\w\-_]+\.pdf(?:\s*,?\s*(?:page|pg|slide)\s*\d+)?/gi, '')
    // Remove lingering page tags like "(Page 8)" or "[Page 8]" if left isolated
    .replace(/\[\s*(?:page|pg|slide)\s*\d+\s*\]/gi, '')
    .replace(/\(\s*(?:page|pg|slide)\s*\d+\s*\)/gi, '')
    // Clean up orphan lead-in attribution phrases like "According to," or "As stated in," left after citation removal
    .replace(/^ *(?:according to|as reported in|as stated in|as per|as highlighted in|per) *,? */gim, '')
    .replace(/\b(?:according to|as reported in|as stated in|as per|as highlighted in) *, */gi, '')
    // Clean up empty parentheses or brackets left behind
    .replace(/\(\s*\)/g, '')
    .replace(/\[\s*\]/g, '')
    // Clean up spaces before punctuation
    .replace(/\s+([,.;:])/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function isRefusalResponse(text) {
  if (!text) return false;
  const lower = text.toLowerCase();
  return (
    lower.includes('strictly dedicated to itc') ||
    lower.includes('dedicated exclusively to itc') ||
    lower.includes('exclusively about itc') ||
    lower.includes('outside the context of itc') ||
    lower.includes('outside the scope of itc') ||
    lower.includes('outside the scope') ||
    lower.includes('outside my scope') ||
    lower.includes('outside my domain') ||
    lower.includes('cannot provide information about') ||
    lower.includes('cannot provide information regarding') ||
    lower.includes('cannot answer questions regarding') ||
    lower.includes('unrelated to itc') ||
    lower.includes('not related to itc') ||
    lower.includes('i cannot assist with') ||
    lower.includes('only assist with inquiries regarding itc') ||
    lower.includes('information exclusively about itc')
  );
}

function isTableLine(line) {
  if (!line) return false;
  const trimmed = line.trim();
  return trimmed.includes('|') && (trimmed.startsWith('|') || trimmed.endsWith('|') || trimmed.split('|').length >= 3);
}

function isTableDivider(line) {
  if (!line) return false;
  const trimmed = line.trim();
  return /^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$/.test(trimmed);
}

function parseTableRow(line) {
  let trimmed = line.trim();
  if (trimmed.startsWith('|')) trimmed = trimmed.slice(1);
  if (trimmed.endsWith('|')) trimmed = trimmed.slice(0, -1);
  return trimmed.split('|').map((cell) => cell.trim());
}

function getAlignments(dividerRow) {
  return dividerRow.map((cell) => {
    const trimmed = cell.trim();
    if (trimmed.startsWith(':') && trimmed.endsWith(':')) return 'center';
    if (trimmed.endsWith(':')) return 'right';
    if (trimmed.startsWith(':')) return 'left';
    return 'left';
  });
}

function renderFormattedContent(text) {
  if (!text) return null;
  const sanitizedText = stripSourceCitations(text);

  const lines = sanitizedText.split('\n');
  const elements = [];
  let currentList = [];
  let isNumbered = false;

  const flushList = () => {
    if (currentList.length > 0) {
      if (isNumbered) {
        elements.push(
          <ol key={`ol-${elements.length}`} className="memo-list numbered">
            {currentList.map((item, idx) => (
              <li key={idx} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
            ))}
          </ol>
        );
      } else {
        elements.push(
          <ul key={`ul-${elements.length}`} className="memo-list bulleted">
            {currentList.map((item, idx) => (
              <li key={idx} dangerouslySetInnerHTML={{ __html: formatInline(item) }} />
            ))}
          </ul>
        );
      }
      currentList = [];
    }
  };

  const formatInline = (str) => {
    return str
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/_([^_]+)_/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code class="memo-code">$1</code>');
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trim();

    if (!line) {
      flushList();
      i++;
      continue;
    }

    // Skip orphan divider lines if encountered outside a table
    if (isTableDivider(line)) {
      i++;
      continue;
    }

    // Detect markdown table: header row followed by divider row
    if (isTableLine(line)) {
      let nextIdx = i + 1;
      while (nextIdx < lines.length && !lines[nextIdx].trim()) {
        nextIdx++;
      }
      if (nextIdx < lines.length && isTableDivider(lines[nextIdx])) {
        flushList();
        const headerRow = parseTableRow(line);
        const dividerRow = parseTableRow(lines[nextIdx]);
        const alignments = getAlignments(dividerRow);
        const rows = [];

        i = nextIdx + 1;
        while (i < lines.length) {
          const curLine = lines[i].trim();
          if (!curLine) {
            let lookahead = i + 1;
            while (lookahead < lines.length && !lines[lookahead].trim()) {
              lookahead++;
            }
            if (lookahead < lines.length && isTableLine(lines[lookahead]) && !isTableDivider(lines[lookahead])) {
              i = lookahead;
              continue;
            } else {
              break;
            }
          }
          if (isTableLine(curLine) && !isTableDivider(curLine)) {
            rows.push(parseTableRow(curLine));
            i++;
          } else {
            break;
          }
        }

        elements.push(
          <div key={`table-wrapper-${elements.length}`} className="memo-table-wrapper">
            <table className="memo-table">
              <thead>
                <tr>
                  {headerRow.map((h, colIdx) => (
                    <th
                      key={colIdx}
                      style={{ textAlign: alignments[colIdx] || 'left' }}
                      dangerouslySetInnerHTML={{ __html: formatInline(h) }}
                    />
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIdx) => (
                  <tr key={rowIdx}>
                    {row.map((cell, colIdx) => (
                      <td
                        key={colIdx}
                        style={{ textAlign: alignments[colIdx] || 'left' }}
                        dangerouslySetInnerHTML={{ __html: formatInline(cell) }}
                      />
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    if (line.startsWith('### ')) {
      flushList();
      elements.push(
        <h3 key={`h3-${elements.length}`} className="memo-h3" dangerouslySetInnerHTML={{ __html: formatInline(line.slice(4)) }} />
      );
    } else if (line.startsWith('## ')) {
      flushList();
      elements.push(
        <h2 key={`h2-${elements.length}`} className="memo-h2" dangerouslySetInnerHTML={{ __html: formatInline(line.slice(3)) }} />
      );
    } else if (line.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={`h1-${elements.length}`} className="memo-h1" dangerouslySetInnerHTML={{ __html: formatInline(line.slice(2)) }} />
      );
    } else if (line.startsWith('- ') || line.startsWith('* ') || line.startsWith('• ')) {
      if (isNumbered && currentList.length > 0) flushList();
      isNumbered = false;
      currentList.push(line.slice(2));
    } else if (/^\d+\.\s/.test(line)) {
      if (!isNumbered && currentList.length > 0) flushList();
      isNumbered = true;
      currentList.push(line.replace(/^\d+\.\s/, ''));
    } else {
      flushList();
      elements.push(
        <p key={`p-${elements.length}`} className="memo-p" dangerouslySetInnerHTML={{ __html: formatInline(line) }} />
      );
    }
    i++;
  }

  flushList();
  return elements;
}

export default function ChatMessage({ message, onSelectResource, onPreviewImage, onFollowUp }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  if (isUser) {
    return (
      <div className="message-user animate-slide-up">
        <div className="user-bubble-wrapper">
          <div className="user-bubble">{message.content}</div>
          <div className="user-avatar-tag">User</div>
        </div>
      </div>
    );
  }

  const { content, citations, visual_context_used, source_type, related_images } = message;
  const cleanText = stripSourceCitations(content);
  const isRefusal = source_type === 'none' || isRefusalResponse(cleanText);

  // Collect displayable flowchart / diagram images strictly when NOT a refusal and source is document
  const displayImages = [];
  const seenUrls = new Set();

  if (!isRefusal && source_type === 'document') {
    if (related_images && related_images.length > 0) {
      related_images.forEach((img) => {
        if (img && img.image_url && !seenUrls.has(img.image_url)) {
          seenUrls.add(img.image_url);
          displayImages.push({
            image_url: img.image_url,
            title: img.title || 'Official Document Flowchart & Architecture',
            page: img.page
          });
        }
      });
    }

    // Fallback to citations if related_images is empty
    if (displayImages.length === 0 && citations && citations.length > 0) {
      citations.forEach((c) => {
        if (c.source_type === 'document' && c.image_url && !seenUrls.has(c.image_url)) {
          seenUrls.add(c.image_url);
          displayImages.push({
            image_url: c.image_url,
            title: c.has_visual ? 'Official Strategy Architecture & Flowchart' : 'Official Document Visual Record',
            page: c.page_number
          });
        }
      });
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(cleanText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="message-assistant animate-slide-up">
      {/* Executive Assistant Header */}
      <div className="assistant-header modern-assistant-header">
        <div className="assistant-identity">
          <div className="assistant-logo-wrapper">
            <img
              src="/itc-logo-clean.webp"
              alt="ITC Logo"
              className="assistant-logo-icon"
              onError={(e) => {
                e.target.onerror = null;
                e.target.src = '/itc-logo.webp';
              }}
            />
          </div>
          <div>
            <div className="assistant-title">
              {isRefusal ? 'ITC Scope & Domain Notice' : 'ITC Corporate Intelligence Synthesis'}
            </div>
            <div className="assistant-subtitle">
              {isRefusal ? 'Domain Scope Advisory' : 'Enterprise Briefing • Official Document Grounding'}
            </div>
          </div>
        </div>

        <div className="assistant-actions">
          <button
            className={`copy-memo-btn-modern ${copied ? 'copied' : ''}`}
            onClick={handleCopy}
            title="Copy intelligence briefing to clipboard"
            type="button"
          >
            {copied ? (
              <>
                <span className="copy-icon">✓</span>
                <span>Copied</span>
              </>
            ) : (
              <>
                <span className="copy-icon">📋</span>
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Synthesis Body */}
      <div className="assistant-body modern-assistant-body">
        {renderFormattedContent(content)}
      </div>

      {/* Official Flowchart & Visual Evidence Showcase - Strictly hidden for refusals or non-document replies */}
      {!isRefusal && displayImages.length > 0 && source_type !== 'none' && (
        <div className="memo-visuals-container animate-fade-in">
          <div className="memo-visuals-header">
            <div className="memo-visuals-tag">
              <span className="visuals-icon">📊</span>
              <span>Official Document Flowchart &amp; Strategy Diagram</span>
            </div>
            <span className="visuals-hint">Click image to inspect in full resolution</span>
          </div>

          <div className="memo-visuals-grid">
            {displayImages.slice(0, 2).map((item, idx) => (
              <div
                key={idx}
                className="memo-visual-card"
                onClick={() => {
                  if (onPreviewImage) {
                    onPreviewImage(item.image_url, item.title);
                  } else if (onSelectResource) {
                    onSelectResource({
                      image_url: item.image_url,
                      title: item.title,
                      source_type: 'document'
                    });
                  }
                }}
                role="button"
                tabIndex={0}
                title="Click to zoom and inspect high-resolution diagram"
              >
                <div className="memo-visual-preview-wrapper">
                  <img
                    src={item.image_url}
                    alt={item.title}
                    className="memo-visual-img"
                    loading="eager"
                    decoding="async"
                  />
                  <div className="memo-visual-overlay">
                    <span className="zoom-badge">🔍 Zoom / Inspect Diagram</span>
                  </div>
                </div>
                <div className="memo-visual-caption">
                  <span className="caption-icon">📑</span>
                  <span className="caption-text">{item.title}</span>
                  <span className="caption-action">Inspect &rarr;</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggested Follow-up Inquiries - Strictly hidden for refusals */}
      {!isRefusal && onFollowUp && source_type !== 'none' && (
        <div className="followup-chips-container modern-followup-tray">
          <span className="followup-label">Follow-up:</span>
          <button
            type="button"
            className="followup-chip-modern"
            onClick={() => onFollowUp('explain this to me in easy language')}
          >
            <span>💡 Explain in easy language</span>
          </button>
          <button
            type="button"
            className="followup-chip-modern"
            onClick={() => onFollowUp('Summarize key takeaways in 3 bullet points')}
          >
            <span>📋 3 Key Takeaways</span>
          </button>
          <button
            type="button"
            className="followup-chip-modern"
            onClick={() => onFollowUp('What are the long-term strategic implications of this for ITC?')}
          >
            <span>📈 Strategic Implications</span>
          </button>
        </div>
      )}
    </div>
  );
}
