import React from 'react';
import { Mail, Send, X, ShieldCheck } from 'lucide-react';

export default function EmailPreviewModal({ emailData, onApprove, onReject }) {
  if (!emailData) return null;

  const { recipient, subject, body, account, action_id } = emailData;

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-card">
        <div className="modal-header">
          <Mail size={24} color="#00f2fe" />
          <div className="modal-title">Email Draft Ready for Approval</div>
        </div>

        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '10px', margin: '1rem 0' }}>
          <div className="review-field-row">
            <span className="review-label">Google Account:</span>
            <span className="review-val" style={{ color: 'var(--accent-cyan)' }}>{account}</span>
          </div>
          <div className="review-field-row">
            <span className="review-label">To:</span>
            <span className="review-val">{recipient}</span>
          </div>
          <div className="review-field-row">
            <span className="review-label">Subject:</span>
            <span className="review-val">{subject}</span>
          </div>
        </div>

        <div style={{ margin: '1rem 0' }}>
          <div className="review-label" style={{ marginBottom: '0.4rem' }}>Email Body Preview:</div>
          <textarea
            readOnly
            value={body}
            rows={5}
            style={{
              width: '100%',
              background: 'rgba(10, 12, 16, 0.8)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-main)',
              borderRadius: '8px',
              padding: '0.8rem',
              fontFamily: 'var(--font-body)',
              fontSize: '0.9rem'
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', color: 'var(--accent-emerald)' }}>
          <ShieldCheck size={16} />
          <span>Security Boundary: Agent paused. Email will NOT be sent until you click Send Email.</span>
        </div>

        <div className="modal-actions">
          <button className="btn-secondary" onClick={() => onReject(action_id)}>
            <X size={16} style={{ marginRight: '0.4rem' }} /> Cancel
          </button>
          <button className="btn-primary" onClick={() => onApprove(action_id)}>
            <Send size={16} style={{ marginRight: '0.4rem' }} /> Send Email Now
          </button>
        </div>
      </div>
    </div>
  );
}
