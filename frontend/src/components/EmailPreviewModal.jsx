import React, { useState } from 'react';
import { Mail, Send, X, ShieldCheck, Edit3 } from 'lucide-react';

export default function EmailPreviewModal({ emailData, onApprove, onReject }) {
  if (!emailData) return null;

  const { recipient, subject, body, account, action_id } = emailData;

  // Editable fields so user can modify before sending
  const [editRecipient, setEditRecipient] = useState(recipient || '');
  const [editSubject, setEditSubject] = useState(subject || '');
  const [editBody, setEditBody] = useState(body || '');

  const handleApproveClick = () => {
    // MUST pass the email payload so the backend knows what to compose
    onApprove(action_id, {
      recipient: editRecipient,
      subject: editSubject,
      body: editBody
    });
  };

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
          <div className="review-field-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.3rem' }}>
            <span className="review-label">To:</span>
            <input
              className="prompt-input"
              style={{ width: '100%', padding: '0.5rem 0.8rem', fontSize: '0.9rem' }}
              value={editRecipient}
              onChange={(e) => setEditRecipient(e.target.value)}
            />
          </div>
          <div className="review-field-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.3rem', marginTop: '0.5rem' }}>
            <span className="review-label">Subject:</span>
            <input
              className="prompt-input"
              style={{ width: '100%', padding: '0.5rem 0.8rem', fontSize: '0.9rem' }}
              value={editSubject}
              onChange={(e) => setEditSubject(e.target.value)}
            />
          </div>
        </div>

        <div style={{ margin: '1rem 0' }}>
          <div className="review-label" style={{ marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Edit3 size={14} /> Email Body (editable):
          </div>
          <textarea
            value={editBody}
            onChange={(e) => setEditBody(e.target.value)}
            rows={5}
            style={{
              width: '100%',
              background: 'rgba(10, 12, 16, 0.8)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-main)',
              borderRadius: '8px',
              padding: '0.8rem',
              fontFamily: 'var(--font-body)',
              fontSize: '0.9rem',
              resize: 'vertical'
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', color: 'var(--accent-emerald)' }}>
          <ShieldCheck size={16} />
          <span>Agent will open Gmail, compose this email, and click Send on your Chrome browser.</span>
        </div>

        <div className="modal-actions">
          <button className="btn-secondary" onClick={() => onReject(action_id)}>
            <X size={16} style={{ marginRight: '0.4rem' }} /> Cancel
          </button>
          <button className="btn-primary" onClick={handleApproveClick}>
            <Send size={16} style={{ marginRight: '0.4rem' }} /> Approve & Send Email
          </button>
        </div>
      </div>
    </div>
  );
}
