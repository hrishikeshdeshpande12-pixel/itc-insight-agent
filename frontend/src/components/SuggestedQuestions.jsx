import React, { useState } from 'react';

const CATEGORIES = [
  { id: 'all', label: 'All Domains' },
  { id: 'strategy', label: 'ITC Next Strategy' },
  { id: 'fmcg', label: 'FMCG Growth' },
  { id: 'value', label: 'Value & Governance' },
  { id: 'esg', label: 'Sustainability 2.0' },
];

const SUGGESTIONS = [
  {
    category: 'strategy',
    icon: '🚀',
    title: 'ITC Next Strategy',
    text: "What is ITC Next and how is it shaping future-readiness?",
    desc: 'Strategic vectors, digitalization, and structural vectors across businesses.'
  },
  {
    category: 'fmcg',
    icon: '🛒',
    title: 'FMCG Growth Platforms',
    text: "What are ITC's FMCG growth platforms and brand pillars?",
    desc: 'Scale expansion, consumer megatrends, and mega-brand ecosystems.'
  },
  {
    category: 'value',
    icon: '💎',
    title: 'Value Creation Model',
    text: "What is ITC's multi-capital value creation model?",
    desc: 'Financial, manufactured, intellectual, human, social, and natural capital.'
  },
  {
    category: 'value',
    icon: '🏛️',
    title: 'Corporate Governance',
    text: "Explain ITC's corporate governance structure and 3-tier framework.",
    desc: 'Board of Directors, Corporate Management Committee, and Divisional Boards.'
  },
  {
    category: 'esg',
    icon: '🌱',
    title: 'Sustainability Priorities',
    text: "What are ITC's sustainability priorities and Net Zero targets?",
    desc: 'Water positive, carbon positive, solid waste recycling, and biodiversity.'
  },
  {
    category: 'esg',
    icon: '🌍',
    title: 'Climate Resilience',
    text: "Explain ITC's approach to climate change and regenerative agriculture.",
    desc: 'TCFD disclosure, renewable energy mix, and climate-smart farming.'
  },
  {
    category: 'fmcg',
    icon: '📦',
    title: 'SKU Scale Transformation',
    text: "According to the FMCG transformation presentation, how did ITC's categories and SKU scale change over time?",
    desc: 'Decadal portfolio expansion from tobacco to multi-category powerhouse.'
  },
  {
    category: 'strategy',
    icon: '📈',
    title: 'Real-time Market Metrics',
    text: "What is the latest ITC stock price and recent market performance?",
    desc: 'Live market valuation, dividend track record, and analyst updates.'
  },
];

export default function SuggestedQuestions({ onSelectQuestion }) {
  const [selectedCategory, setSelectedCategory] = useState('all');

  const filtered = selectedCategory === 'all'
    ? SUGGESTIONS
    : SUGGESTIONS.filter((s) => s.category === selectedCategory);

  return (
    <div className="suggested-section modern-suggested-section">
      <div className="suggested-header-bar">
        <span className="suggested-section-title">Strategic Exploration Topics</span>
        <div className="category-filter-pills">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              type="button"
              className={`cat-filter-btn ${selectedCategory === cat.id ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat.id)}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      <div className="suggested-cards-grid">
        {filtered.map((item, idx) => (
          <div
            key={idx}
            className="suggested-modern-card"
            onClick={() => onSelectQuestion(item.text)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onSelectQuestion(item.text);
              }
            }}
          >
            <div className="card-top-line">
              <span className="card-icon">{item.icon}</span>
              <span className="card-category-label">{item.title}</span>
            </div>
            <p className="card-query-text">{item.text}</p>
            <span className="card-query-desc">{item.desc}</span>
            <div className="card-hover-arrow">&rarr;</div>
          </div>
        ))}
      </div>
    </div>
  );
}
