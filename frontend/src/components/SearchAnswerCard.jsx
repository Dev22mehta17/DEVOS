import React from 'react';
import { Sparkles, Globe, ExternalLink, X, CheckCircle, Info, ArrowUpRight } from 'lucide-react';

export default function SearchAnswerCard({ searchResult, onClose }) {
  if (!searchResult) return null;

  const { query, direct_answer, key_facts = [], sources = [], search_url } = searchResult;

  if (!direct_answer && key_facts.length === 0 && sources.length === 0) return null;

  return (
    <div
      className="glass-panel"
      style={{
        background: 'linear-gradient(135deg, rgba(16, 24, 38, 0.95) 0%, rgba(13, 17, 23, 0.95) 100%)',
        border: '1px solid rgba(0, 242, 254, 0.35)',
        boxShadow: '0 8px 32px rgba(0, 242, 254, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
        borderRadius: '12px',
        padding: '1.25rem',
        marginBottom: '1rem',
        animation: 'fadeIn 0.25s ease-out'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            style={{
              background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
              padding: '6px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 10px rgba(0,242,254,0.3)'
            }}
          >
            <Sparkles size={16} color="#000" />
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--accent-cyan)', fontWeight: 600 }}>
              Live Web Intelligence
            </div>
            <div style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-main)' }}>
              {query ? `"${query}"` : 'Search Result'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {search_url && (
            <a
              href={search_url}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.3rem',
                fontSize: '0.76rem',
                color: 'var(--text-muted)',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-color)',
                padding: '4px 8px',
                borderRadius: '6px',
                textDecoration: 'none',
                transition: 'all 0.15s'
              }}
            >
              <span>Google</span>
              <ArrowUpRight size={13} />
            </a>
          )}
          {onClose && (
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
                borderRadius: '4px'
              }}
              title="Dismiss"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Direct Answer Box */}
      {direct_answer && (
        <div
          style={{
            background: 'rgba(0, 242, 254, 0.06)',
            border: '1px solid rgba(0, 242, 254, 0.2)',
            borderRadius: '8px',
            padding: '0.9rem 1rem',
            marginBottom: '0.85rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.74rem', color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '0.35rem' }}>
            <CheckCircle size={14} />
            <span>DIRECT ANSWER</span>
          </div>
          <div style={{ fontSize: '0.95rem', lineHeight: 1.55, color: '#f0f6fc', fontWeight: 500 }}>
            {direct_answer}
          </div>
        </div>
      )}

      {/* Key Facts / Highlights */}
      {key_facts && key_facts.length > 0 && (
        <div style={{ marginBottom: '0.85rem' }}>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Info size={13} />
            <span>Key Facts</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.4rem' }}>
            {key_facts.map((fact, idx) => {
              const [label, ...valParts] = fact.split(':');
              const val = valParts.join(':').trim();
              return (
                <div
                  key={idx}
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.07)',
                    borderRadius: '6px',
                    padding: '0.45rem 0.65rem',
                    fontSize: '0.82rem'
                  }}
                >
                  <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{label}: </span>
                  <span style={{ color: 'var(--text-main)' }}>{val || fact}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top Web Sources */}
      {sources && sources.length > 0 && (
        <div>
          <div style={{ fontSize: '0.74rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Globe size={13} />
            <span>Top Web Sources</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.45rem' }}>
            {sources.map((src, idx) => (
              <a
                key={idx}
                href={src.url}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'block',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '0.5rem 0.7rem',
                  textDecoration: 'none',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(0, 242, 254, 0.05)';
                  e.currentTarget.style.borderColor = 'rgba(0, 242, 254, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {src.source || 'Web Source'}
                  </span>
                  <ExternalLink size={11} color="var(--text-muted)" />
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-main)', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {src.title}
                </div>
                {src.snippet && (
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '0.2rem', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', lineHeight: 1.35 }}>
                    {src.snippet}
                  </div>
                )}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
