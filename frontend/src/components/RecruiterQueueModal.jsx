import React, { useState } from 'react';
import { ShieldCheck, Mail, Send, CheckCircle2, AlertCircle, X, Paperclip, Clock, Sparkles } from 'lucide-react';

export default function RecruiterQueueModal({ queueData, onApproveItem, onApproveAll, onClose }) {
  if (!queueData || !queueData.items || queueData.items.length === 0) return null;

  const [items, setItems] = useState(queueData.items);
  const [submittingIds, setSubmittingIds] = useState(new Set());

  const handleTextChange = (id, newBody) => {
    setItems(prev => prev.map(item => item.action_id === id ? { ...item, body: newBody } : item));
  };

  const handleSingleApprove = async (item) => {
    setSubmittingIds(prev => new Set(prev).add(item.action_id));
    await onApproveItem(item.action_id, item);
    setItems(prev => prev.filter(i => i.action_id !== item.action_id));
    setSubmittingIds(prev => {
      const next = new Set(prev);
      next.delete(item.action_id);
      return next;
    });
  };

  const handleBatchApprove = async () => {
    for (const item of items) {
      setSubmittingIds(prev => new Set(prev).add(item.action_id));
      await onApproveItem(item.action_id, item);
    }
    setItems([]);
    if (onClose) onClose();
  };

  const getCategoryBadge = (cat) => {
    switch (cat) {
      case 'INTERVIEW_INVITE':
        return { label: '🎉 Interview Invite', bg: 'rgba(16, 185, 129, 0.15)', color: '#10b981', border: 'rgba(16, 185, 129, 0.3)' };
      case 'ONLINE_ASSESSMENT':
        return { label: '⚡ Online Assessment', bg: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', border: 'rgba(245, 158, 11, 0.3)' };
      case 'REJECTION':
        return { label: 'ℹ️ Graceful Follow-up', bg: 'rgba(156, 163, 175, 0.15)', color: '#9ca3af', border: 'rgba(156, 163, 175, 0.3)' };
      default:
        return { label: '📬 Recruiter Outreach', bg: 'rgba(0, 242, 254, 0.15)', color: '#00f2fe', border: 'rgba(0, 242, 254, 0.3)' };
    }
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 1000 }}>
      <div
        className="glass-panel modal-card"
        style={{
          maxWidth: '820px',
          width: '94%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          border: '1px solid rgba(0, 242, 254, 0.4)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.8), 0 0 40px rgba(0, 242, 254, 0.15)'
        }}
      >
        {/* Modal Header */}
        <div className="modal-header" style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ background: 'linear-gradient(135deg, #00f2fe, #4facfe)', padding: '8px', borderRadius: '10px' }}>
              <Mail color="#000" size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <span className="modal-title" style={{ fontSize: '1.15rem' }}>Recruiter Inbox Triage Queue</span>
                <span style={{ fontSize: '0.74rem', background: 'rgba(0,242,254,0.15)', color: 'var(--accent-cyan)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600 }}>
                  {items.length} Actions Pending
                </span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Review, edit, and approve personalized responses before dispatching to Chrome.
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {items.length > 1 && (
              <button
                className="action-btn"
                onClick={handleBatchApprove}
                style={{ padding: '0.45rem 0.9rem', fontSize: '0.82rem', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
              >
                <CheckCircle2 size={15} /> Approve All ({items.length})
              </button>
            )}
            <button
              onClick={onClose}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Scanned Keywords Filter Indicator */}
        {queueData.scanned_keywords && queueData.scanned_keywords.length > 0 && (
          <div style={{ padding: '0.6rem 1.5rem', background: 'rgba(0,0,0,0.3)', borderBottom: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontWeight: 500 }}>🔍 Filter Keywords:</span>
            {queueData.scanned_keywords.map((kw, idx) => (
              <span key={idx} style={{ fontSize: '0.72rem', background: 'rgba(255,255,255,0.06)', color: 'var(--accent-cyan)', padding: '2px 8px', borderRadius: '6px', border: '1px solid rgba(0,242,254,0.2)' }}>
                {kw}
              </span>
            ))}
          </div>
        )}

        {/* Scrollable Items List */}
        <div style={{ overflowY: 'auto', padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {items.map((item) => {
            const badge = getCategoryBadge(item.category);
            const isSubmitting = submittingIds.has(item.action_id);

            return (
              <div
                key={item.action_id}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '10px',
                  padding: '1.1rem',
                  position: 'relative'
                }}
              >
                {/* Item Top Bar */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.7rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span
                      style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        background: badge.bg,
                        color: badge.color,
                        border: `1px solid ${badge.border}`,
                        padding: '2px 8px',
                        borderRadius: '6px'
                      }}
                    >
                      {badge.label}
                    </span>
                    <span style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      To: {item.recipient}
                    </span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {item.date || 'Recent'}
                  </span>
                </div>

                {/* Original Snippet */}
                {item.original_snippet && (
                  <div
                    style={{
                      background: 'rgba(0, 0, 0, 0.25)',
                      borderRadius: '6px',
                      padding: '0.5rem 0.75rem',
                      fontSize: '0.78rem',
                      color: 'var(--text-muted)',
                      marginBottom: '0.75rem',
                      borderLeft: '2px solid var(--accent-cyan)'
                    }}
                  >
                    <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>Thread: </span>
                    {item.original_snippet}
                  </div>
                )}

                {/* Subject & Body Editor */}
                <div style={{ marginBottom: '0.6rem' }}>
                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.2rem' }}>
                    Subject: {item.subject}
                  </div>
                  <textarea
                    rows={4}
                    value={item.body}
                    onChange={(e) => handleTextChange(item.action_id, e.target.value)}
                    style={{
                      width: '100%',
                      background: 'rgba(0, 0, 0, 0.4)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '6px',
                      padding: '0.6rem',
                      fontSize: '0.84rem',
                      color: '#f0f6fc',
                      fontFamily: 'inherit',
                      lineHeight: 1.45,
                      resize: 'vertical'
                    }}
                  />
                </div>

                {/* Footer Controls */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.6rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
                    {item.attach_resume && (
                      <>
                        <Paperclip size={13} />
                        <span>Dev_Resume.pdf attached</span>
                      </>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      className="reject-btn"
                      onClick={() => setItems(prev => prev.filter(i => i.action_id !== item.action_id))}
                      style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}
                    >
                      Dismiss
                    </button>
                    <button
                      className="approve-btn"
                      onClick={() => handleSingleApprove(item)}
                      disabled={isSubmitting}
                      style={{ padding: '0.4rem 0.85rem', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      <Send size={13} />
                      {isSubmitting ? 'Sending on Chrome...' : 'Approve & Send'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
