import React, { useState, useEffect } from 'react';
import { FileText, CheckCircle, AlertTriangle, Send, X, Paperclip, FileUp } from 'lucide-react';

export default function FormReviewModal({ formData, onApprove, onReject }) {
  if (!formData) return null;

  const { form_url, page_title, filled_fields, flagged_fields, action_id, uploaded_resume, available_resumes } = formData;

  const [fields, setFields] = useState([]);
  const [selectedResume, setSelectedResume] = useState(uploaded_resume || '');
  const [resumeList, setResumeList] = useState([]);
  const [customUploadMsg, setCustomUploadMsg] = useState('');

  useEffect(() => {
    if (filled_fields) {
      // Deduplicate fields (remove duplicate file upload rows)
      const unique = [];
      const seen = new Set();
      filled_fields.forEach(f => {
        if (f.is_file) return;
        if (!seen.has(f.field_label)) {
          seen.add(f.field_label);
          unique.push({ ...f });
        }
      });
      setFields(unique);
    }

    const available = available_resumes && available_resumes.length > 0
      ? [...available_resumes]
      : (uploaded_resume ? [uploaded_resume] : []);

    setResumeList(available);
    if (uploaded_resume && !selectedResume) {
      setSelectedResume(uploaded_resume);
    } else if (available.length > 0 && !selectedResume) {
      setSelectedResume(available[0]);
    }
  }, [formData]);

  const handleCustomUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setCustomUploadMsg(`Uploading '${file.name}'...`);
    const formDataObj = new FormData();
    formDataObj.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/memory/upload', {
        method: 'POST',
        body: formDataObj
      });
      const result = await res.json();
      if (result.status === 'SUCCESS') {
        const filePath = result.filename;
        setResumeList(prev => [filePath, ...prev]);
        setSelectedResume(filePath);
        setCustomUploadMsg(`✓ Attached '${file.name}'!`);
        setTimeout(() => setCustomUploadMsg(''), 4000);
      }
    } catch (err) {
      console.error('Upload error:', err);
      setCustomUploadMsg('Upload failed.');
    }
  };

  const handleFieldChange = (index, newValue) => {
    const updated = [...fields];
    updated[index].value = newValue;
    setFields(updated);
  };

  const handleApproveSubmit = () => {
    onApprove(action_id, {
      form_url: form_url,
      updated_fields: fields,
      selected_resume: selectedResume
    });
  };

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

        {/* Resume Selection Dropdown & Custom Upload */}
        <div style={{ background: 'rgba(0, 242, 254, 0.08)', border: '1px solid var(--accent-cyan)', padding: '0.86rem 1rem', borderRadius: '10px', marginBottom: '1.2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
              <Paperclip size={18} />
              <span>Select Resume File to Attach:</span>
            </div>
            <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-purple)', fontSize: '0.82rem', fontWeight: 600, background: 'rgba(127,0,255,0.15)', padding: '0.3rem 0.6rem', borderRadius: '6px', border: '1px solid var(--accent-purple)' }}>
              <FileUp size={14} />
              <span>+ Upload New Resume</span>
              <input type="file" accept=".pdf,.docx,.doc" onChange={handleCustomUpload} style={{ display: 'none' }} />
            </label>
          </div>

          {customUploadMsg && (
            <div style={{ fontSize: '0.78rem', color: 'var(--accent-emerald)', marginBottom: '0.4rem', fontWeight: 500 }}>
              {customUploadMsg}
            </div>
          )}

          {resumeList.length > 0 ? (
            <select
              value={selectedResume}
              onChange={(e) => setSelectedResume(e.target.value)}
              style={{
                width: '100%',
                background: 'rgba(10, 12, 16, 0.9)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-main)',
                padding: '0.6rem 0.8rem',
                borderRadius: '8px',
                fontFamily: 'var(--font-body)',
                fontSize: '0.88rem',
                outline: 'none'
              }}
            >
              {resumeList.map((resPath, i) => (
                <option key={i} value={resPath}>
                  {resPath.split('/').pop()} ({resPath})
                </option>
              ))}
            </select>
          ) : (
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              No local resume detected. Click '+ Upload New Resume' above to attach your file.
            </div>
          )}
        </div>

        {/* Editable Form Inputs */}
        <div style={{ maxHeight: '280px', overflowY: 'auto', marginBottom: '1rem', paddingRight: '0.5rem' }}>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.6rem' }}>
            Review & Edit Form Inputs ({fields.length}):
          </div>
          {fields.map((f, i) => (
            <div key={i} className="review-field-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.3rem', padding: '0.6rem 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', fontSize: '0.85rem' }}>
                <span className="review-label" style={{ fontWeight: 600, color: 'var(--text-muted)' }}>{f.field_label}:</span>
                {f.is_ai_generated && <span style={{ fontSize: '0.7rem', background: 'rgba(127,0,255,0.2)', color: 'var(--accent-purple)', padding: '2px 6px', borderRadius: '4px' }}>AI Answer</span>}
              </div>
              <input
                className="prompt-input"
                style={{ width: '100%', padding: '0.55rem 0.8rem', fontSize: '0.9rem' }}
                value={f.value}
                onChange={(e) => handleFieldChange(i, e.target.value)}
              />
            </div>
          ))}
        </div>

        {flagged_fields && flagged_fields.length > 0 && (
          <div className="flagged-box">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              <AlertTriangle size={16} />
              <span>{flagged_fields.length} Fields Require Manual Attention:</span>
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
          <button className="btn-primary" onClick={handleApproveSubmit}>
            <CheckCircle size={16} style={{ marginRight: '0.4rem' }} /> Approve & Submit Form
          </button>
        </div>
      </div>
    </div>
  );
}
