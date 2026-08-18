import React, { useState } from 'react';
import { Mail, Send, X, ShieldCheck, Edit3, Paperclip, Reply, CornerUpRight, Sparkles } from 'lucide-react';

export default function EmailPreviewModal({ emailData, onApprove, onReject }) {
  if (!emailData) return null;

  const { recipient, subject, body, account, action_id, action_kind, original_snippet, attached_file } = emailData;

  const [editRecipient, setEditRecipient] = useState(recipient || '');
  const [editSubject, setEditSubject] = useState(subject || '');
  const [editBody, setEditBody] = useState(body || '');
  const [editAttachedFile, setEditAttachedFile] = useState(attached_file || '');

  const handleApproveClick = () => {
    onApprove(action_id, {
      recipient: editRecipient,
      subject: editSubject,
      body: editBody,
      attached_file: editAttachedFile
    });
  };

  const isReply = action_kind === 'REPLY';
  const isForward = action_kind === 'FORWARD';

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-card" style={{ maxWidth: '680px' }}>
        <div className="modal-header">
          {isReply ? (
            <Reply size={24} color="#00f2fe" />
          ) : isForward ? (
            <CornerUpRight size={24} color="#00f2fe" />
          ) : (
            <Mail size={24} color="#00f2fe" />
          )}
          <div>
            <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span>{isReply ? 'Reply Draft Ready' : isForward ? 'Forward Draft Ready' : 'Email Draft Ready'}</span>
              <span style={{ fontSize: '0.72rem', background: 'rgba(0,242,254,0.15)', color: 'var(--accent-cyan)', padding: '2px 8px', borderRadius: '4px' }}>
                {action_kind || 'COMPOSE'}
              </span>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Using {account}</div>
          </div>
        </div>

        {/* Original Thread Snippet if Reply / Forward */}
        {original_snippet && (
          <div style={{ background: 'rgba(255,255,255,0.03)', borderLeft: '3px solid var(--accent-purple)', padding: '0.6rem 0.8rem', borderRadius: '4px', margin: '0.8rem 0', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            <span style={{ fontWeight: 600, color: 'var(--accent-purple)' }}>Original Email: </span>
            {original_snippet.slice(0, 160)}...
          </div>
        )}

        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '0.8rem 1rem', borderRadius: '10px', margin: '0.8rem 0' }}>
          <div className="review-field-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.25rem' }}>
            <span className="review-label">To:</span>
            <input
              className="prompt-input"
              style={{ width: '100%', padding: '0.5rem 0.8rem', fontSize: '0.88rem' }}
              value={editRecipient}
              onChange={(e) => setEditRecipient(e.target.value)}
            />
          </div>
          <div className="review-field-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.25rem', marginTop: '0.5rem' }}>
            <span className="review-label">Subject:</span>
            <input
              className="prompt-input"
              style={{ width: '100%', padding: '0.5rem 0.8rem', fontSize: '0.88rem' }}
              value={editSubject}
              onChange={(e) => setEditSubject(e.target.value)}
            />
          </div>
        </div>

        {/* Attachment Indicator */}
        {editAttachedFile && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(0, 230, 118, 0.08)', border: '1px solid var(--accent-emerald)', padding: '0.5rem 0.8rem', borderRadius: '8px', marginBottom: '0.8rem', fontSize: '0.84rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-emerald)' }}>
              <Paperclip size={14} />
              <span>Attached: <strong>{editAttachedFile.split('/').pop()}</strong></span>
            </div>
            <button
              type="button"
              onClick={() => setEditAttachedFile('')}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.78rem' }}
            >
              Remove
            </button>
          </div>
        )}

        <div style={{ margin: '0.8rem 0' }}>
          <div className="review-label" style={{ marginBottom: '0.4rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Edit3 size={14} /> Email Body (includes social signature):
          </div>
          <textarea
            value={editBody}
            onChange={(e) => setEditBody(e.target.value)}
            rows={7}
            style={{
              width: '100%',
              background: 'rgba(10, 12, 16, 0.8)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-main)',
              borderRadius: '8px',
              padding: '0.8rem',
              fontFamily: 'var(--font-body)',
              fontSize: '0.88rem',
              resize: 'vertical',
              lineHeight: 1.5
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', color: 'var(--accent-emerald)' }}>
          <ShieldCheck size={16} />
          <span>Agent will open Gmail, populate this draft & attachments, and execute live on Chrome.</span>
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
