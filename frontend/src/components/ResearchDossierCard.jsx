import React from 'react';
import { Microscope, Globe, ExternalLink, X, CheckCircle, Info, ArrowUpRight, Scale, Sparkles, BookOpen } from 'lucide-react';

export default function ResearchDossierCard({ dossier, onClose }) {
  if (!dossier) return null;

  const {
    title,
    query,
    entities = [],
    executive_summary,
    key_facts = [],
    comparison_matrix = [],
    key_takeaway,
    sources = []
  } = dossier;

  return (
    <div
      className="glass-panel"
      style={{
        background: 'linear-gradient(135deg, rgba(13, 20, 36, 0.96) 0%, rgba(10, 14, 23, 0.96) 100%)',
        border: '1px solid rgba(0, 242, 254, 0.4)',
        boxShadow: '0 12px 40px rgba(0, 242, 254, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1)',
        borderRadius: '14px',
        padding: '1.4rem',
        marginBottom: '1.25rem',
        animation: 'fadeIn 0.25s ease-out'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
          <div
            style={{
              background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
              padding: '7px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 12px rgba(0,242,254,0.35)'
            }}
          >
            <Microscope size={18} color="#000" />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.09em', color: 'var(--accent-cyan)', fontWeight: 700 }}>
              Deep Web Intelligence Dossier
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)' }}>
              {title || `Research: "${query}"`}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.72rem', background: 'rgba(0,242,254,0.1)', color: 'var(--accent-cyan)', border: '1px solid rgba(0,242,254,0.25)', padding: '3px 8px', borderRadius: '12px' }}>
            Multi-Hop Synthesis
          </span>
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
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* Executive Summary */}
      {executive_summary && (
        <div
          style={{
            background: 'rgba(0, 242, 254, 0.05)',
            border: '1px solid rgba(0, 242, 254, 0.2)',
            borderRadius: '10px',
            padding: '1rem 1.1rem',
            marginBottom: '1rem'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--accent-cyan)', fontWeight: 700, marginBottom: '0.4rem' }}>
            <Sparkles size={14} />
            <span>EXECUTIVE SUMMARY</span>
          </div>
          <div style={{ fontSize: '0.92rem', lineHeight: 1.6, color: '#f0f6fc', fontWeight: 400 }}>
            {executive_summary}
          </div>
        </div>
      )}

      {/* Comparison Matrix Table (if comparing entities) */}
      {comparison_matrix && comparison_matrix.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--accent-cyan)', fontWeight: 700, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Scale size={14} />
            <span>Feature & Pricing Comparison Matrix</span>
          </div>
          <div style={{ overflowX: 'auto', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ background: 'rgba(255, 255, 255, 0.04)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.65rem 0.85rem', color: 'var(--text-muted)', fontWeight: 600, width: '25%' }}>Metric</th>
                  <th style={{ padding: '0.65rem 0.85rem', color: 'var(--accent-cyan)', fontWeight: 700, width: '37.5%' }}>
                    {entities[0] || 'Entity 1'}
                  </th>
                  <th style={{ padding: '0.65rem 0.85rem', color: '#a78bfa', fontWeight: 700, width: '37.5%' }}>
                    {entities[1] || 'Entity 2'}
                  </th>
                </tr>
              </thead>
              <tbody>
                {comparison_matrix.map((row, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: idx < comparison_matrix.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
                      background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)'
                    }}
                  >
                    <td style={{ padding: '0.6rem 0.85rem', color: 'var(--text-muted)', fontWeight: 600 }}>{row.metric}</td>
                    <td style={{ padding: '0.6rem 0.85rem', color: 'var(--text-main)' }}>{row.entity_1}</td>
                    <td style={{ padding: '0.6rem 0.85rem', color: 'var(--text-main)' }}>{row.entity_2}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Key Takeaway / Verdict */}
      {key_takeaway && (
        <div
          style={{
            background: 'rgba(167, 139, 250, 0.08)',
            border: '1px solid rgba(167, 139, 250, 0.25)',
            borderRadius: '8px',
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.6rem'
          }}
        >
          <CheckCircle size={16} color="#a78bfa" style={{ marginTop: '2px', flexShrink: 0 }} />
          <div>
            <span style={{ color: '#a78bfa', fontWeight: 700, fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Key Takeaway: {' '}
            </span>
            <span style={{ fontSize: '0.88rem', color: 'var(--text-main)', lineHeight: 1.45 }}>
              {key_takeaway}
            </span>
          </div>
        </div>
      )}

      {/* Sources Grid */}
      {sources && sources.length > 0 && (
        <div>
          <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Globe size={12} />
            <span>Verified Primary Sources ({sources.length})</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.45rem' }}>
            {sources.map((src, idx) => (
              <a
                key={idx}
                href={src.url}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '6px',
                  padding: '0.45rem 0.65rem',
                  textDecoration: 'none',
                  transition: 'all 0.15s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(0, 242, 254, 0.06)';
                  e.currentTarget.style.borderColor = 'rgba(0, 242, 254, 0.3)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  e.currentTarget.style.borderColor = 'var(--border-color)';
                }}
              >
                <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                    {src.source || 'Verified Source'}
                  </div>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {src.title}
                  </div>
                </div>
                <ArrowUpRight size={13} color="var(--text-muted)" style={{ flexShrink: 0, marginLeft: '4px' }} />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
