import React from 'react';
import { FileText, CheckCircle, AlertTriangle, Send, X, Paperclip } from 'lucide-react';

export default function FormReviewModal({ formData, onApprove, onReject }) {
  if (!formData) return null;

  const { form_url, page_title, filled_fields, flagged_fields, action_id, uploaded_resume } = formData;

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-card" style={{ maxWidth: '750px' }}>
        <div className="modal-header">
          <FileText size={24} color="#00e676" />
          <div>
            <div className="modal-title">Form Application Review Sheet</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Target: {page_title} ({form_url})</div>
          </div>
        </div>

        {uploaded_resume && (
          <div style={{ background: 'rgba(0, 242, 254, 0.1)', border: '1px solid var(--accent-cyan)', padding: '0.75rem 1rem', borderRadius: '8px', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.85rem' }}>
            <Paperclip size={18} color="#00f2fe" />
            <span>Attached Local Resume: <strong>{uploaded_resume}</strong></span>
          </div>
        )}

        <div style={{ maxHeight: '280px', overflowY: 'auto', marginBottom: '1rem', paddingRight: '0.5rem' }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.5rem' }}>
            Auto-Filled & AI Generated Inputs ({filled_fields.length}):
          </div>
          {filled_fields.map((f, i) => (
            <div key={i} className="review-field-row">
              <span className="review-label">{f.field_label}:</span>
              <span className="review-val" style={{ color: f.is_ai_generated ? 'var(--accent-purple)' : 'var(--text-main)' }}>
                {f.value} {f.is_ai_generated && <span style={{ fontSize: '0.7rem', background: 'rgba(127,0,255,0.2)', padding: '2px 6px', borderRadius: '4px' }}>AI Answer</span>}
              </span>
            </div>
          ))}
        </div>

        {flagged_fields && flagged_fields.length > 0 && (
          <div className="flagged-box">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              <AlertTriangle size={16} />
              <span>{flagged_fields.length} Fields Require Manual Confirmation / Attention:</span>
            </div>
            {flagged_fields.map((f, i) => (
              <div key={i} style={{ fontSize: '0.82rem', marginLeft: '1.2rem', marginTop: '0.2rem' }}>
                • <strong>{f.field_label}</strong>: {f.reason}
              </div>
            ))}
          </div>
        )}

        <div className="modal-actions">
          <button className="btn-secondary" onClick={() => onReject(action_id)}>
            <X size={16} style={{ marginRight: '0.4rem' }} /> Cancel
          </button>
          <button className="btn-primary" onClick={() => onApprove(action_id)}>
            <CheckCircle size={16} style={{ marginRight: '0.4rem' }} /> Approve & Submit Form
          </button>
        </div>
      </div>
    </div>
  );
}
