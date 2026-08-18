import React, { useState, useEffect } from 'react';
import { FileText, CheckCircle, AlertTriangle, Send, X, Paperclip, FileUp, Sparkles, RefreshCw, Edit3 } from 'lucide-react';

export default function FormReviewModal({ formData, onApprove, onReject }) {
  if (!formData) return null;

  const { form_url, page_title, filled_fields, flagged_fields, action_id, uploaded_resume, available_resumes } = formData;

  const [fields, setFields] = useState([]);
  const [userAnswers, setUserAnswers] = useState({});
  const [selectedResume, setSelectedResume] = useState(uploaded_resume || '');
  const [resumeList, setResumeList] = useState([]);
  const [customUploadMsg, setCustomUploadMsg] = useState('');
  const [generatingFieldIdx, setGeneratingFieldIdx] = useState(null);

  useEffect(() => {
    if (filled_fields) {
      const unique = [];
      const seen = new Set();
      filled_fields.forEach(f => {
        const key = f.field_label + '_' + (f.fieldType || 'text');
        if (f.is_file) return;
        if (!seen.has(key)) {
          seen.add(key);
          unique.push({ ...f });
        }
      });
      setFields(unique);
    }

    if (flagged_fields) {
      const answers = {};
      flagged_fields.forEach((f, i) => {
        answers[i] = f.fieldType === 'checkbox' ? [] : '';
      });
      setUserAnswers(answers);
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

  const handleFlaggedChange = (index, newValue) => {
    setUserAnswers(prev => ({ ...prev, [index]: newValue }));
  };

  const handleCheckboxToggle = (flagIndex, option) => {
    setUserAnswers(prev => {
      const current = Array.isArray(prev[flagIndex]) ? [...prev[flagIndex]] : [];
      if (current.includes(option)) {
        return { ...prev, [flagIndex]: current.filter(o => o !== option) };
      } else {
        return { ...prev, [flagIndex]: [...current, option] };
      }
    });
  };

  const handleRegenerateAI = async (index, label) => {
    setGeneratingFieldIdx(index);
    try {
      const res = await fetch('http://localhost:8000/api/generate-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: label,
          context_hints: `${page_title} ${form_url}`
        })
      });
      const data = await res.json();
      if (data.answer) {
        handleFieldChange(index, data.answer);
      }
    } catch (err) {
      console.error('AI answer generation error:', err);
    } finally {
      setGeneratingFieldIdx(null);
    }
  };

  const handleGenerateFlaggedAI = async (flagIdx, label) => {
    setGeneratingFieldIdx(`flag_${flagIdx}`);
    try {
      const res = await fetch('http://localhost:8000/api/generate-answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: label,
          context_hints: `${page_title} ${form_url}`
        })
      });
      const data = await res.json();
      if (data.answer) {
        handleFlaggedChange(flagIdx, data.answer);
      }
    } catch (err) {
      console.error('AI answer generation error:', err);
    } finally {
      setGeneratingFieldIdx(null);
    }
  };

  const handleApproveSubmit = () => {
    const mergedFields = [...fields];
    if (flagged_fields) {
      flagged_fields.forEach((f, i) => {
        const answer = userAnswers[i];
        if (answer && (typeof answer === 'string' ? answer.trim() : answer.length > 0)) {
          mergedFields.push({
            field_label: f.field_label,
            field_id: f.field_id,
            value: Array.isArray(answer) ? answer.join(', ') : answer,
            fieldType: f.fieldType || 'text',
            questionIndex: f.questionIndex,
            options: f.options
          });
        }
      });
    }

    onApprove(action_id, {
      form_url: form_url,
      updated_fields: mergedFields,
      selected_resume: selectedResume
    });
  };

  const inputStyle = {
    width: '100%',
    background: 'rgba(10, 12, 16, 0.9)',
    border: '1px solid var(--border-color)',
    color: 'var(--text-main)',
    padding: '0.55rem 0.8rem',
    borderRadius: '8px',
    fontFamily: 'var(--font-body)',
    fontSize: '0.88rem',
    outline: 'none'
  };

  const selectStyle = {
    ...inputStyle,
    cursor: 'pointer',
    appearance: 'auto'
  };

  const badgeStyle = (color, bgColor) => ({
    fontSize: '0.7rem',
    background: bgColor,
    color: color,
    padding: '2px 8px',
    borderRadius: '4px',
    fontWeight: 600,
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.2rem'
  });

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-card" style={{ maxWidth: '800px', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
        <div className="modal-header" style={{ marginBottom: '1rem' }}>
          <FileText size={24} color="#00e676" />
          <div>
            <div className="modal-title">Application & Form Review Sheet</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Target: {page_title} ({form_url})</div>
          </div>
        </div>

        {/* Resume Selection Dropdown & Custom Upload */}
        <div style={{ background: 'rgba(0, 242, 254, 0.08)', border: '1px solid var(--accent-cyan)', padding: '0.86rem 1rem', borderRadius: '10px', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>
              <Paperclip size={18} />
              <span>Select Resume to Attach:</span>
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
            <select value={selectedResume} onChange={(e) => setSelectedResume(e.target.value)} style={selectStyle}>
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

        {/* Scrollable Form Body */}
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem', marginBottom: '1rem' }}>
          {/* Auto-filled Fields */}
          <div style={{ marginBottom: '1.2rem' }}>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '0.6rem' }}>
              ✅ Auto-populated Fields ({fields.length}):
            </div>
            {fields.map((f, i) => {
              const isLongText = (f.value && f.value.length > 60) || f.is_ai_generated;
              return (
                <div key={i} className="review-field-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '0.3rem', padding: '0.5rem 0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', fontSize: '0.85rem' }}>
                    <span className="review-label" style={{ fontWeight: 600, color: 'var(--text-muted)' }}>{f.field_label}:</span>
                    <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                      {f.is_ai_generated && (
                        <span style={badgeStyle('var(--accent-purple)', 'rgba(127,0,255,0.2)')}>
                          <Sparkles size={11} /> {f.ai_company ? `${f.ai_company} Context` : 'AI Generated'}
                        </span>
                      )}
                      {f.is_auto_matched && <span style={badgeStyle('var(--accent-emerald)', 'rgba(0,230,118,0.15)')}>Auto-matched</span>}
                      {f.fieldType && f.fieldType !== 'text' && (
                        <span style={badgeStyle('var(--accent-cyan)', 'rgba(0,242,254,0.15)')}>{f.fieldType}</span>
                      )}
                      {/* Re-generate button for long text / AI answers */}
                      {isLongText && (
                        <button
                          type="button"
                          onClick={() => handleRegenerateAI(i, f.field_label)}
                          disabled={generatingFieldIdx === i}
                          style={{
                            background: 'transparent',
                            border: '1px solid rgba(127,0,255,0.4)',
                            color: 'var(--accent-purple)',
                            fontSize: '0.72rem',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.2rem'
                          }}
                        >
                          <RefreshCw size={10} className={generatingFieldIdx === i ? 'animate-spin' : ''} />
                          {generatingFieldIdx === i ? 'Synthesizing...' : 'Re-generate'}
                        </button>
                      )}
                    </div>
                  </div>

                  {(f.fieldType === 'radio' || f.fieldType === 'dropdown') && f.options ? (
                    <select
                      value={f.value}
                      onChange={(e) => handleFieldChange(i, e.target.value)}
                      style={selectStyle}
                    >
                      <option value="">— Select —</option>
                      {f.options.map((opt, oi) => (
                        <option key={oi} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : isLongText ? (
                    <textarea
                      className="prompt-input"
                      rows={3}
                      style={{ width: '100%', padding: '0.55rem 0.8rem', fontSize: '0.88rem', resize: 'vertical' }}
                      value={f.value}
                      onChange={(e) => handleFieldChange(i, e.target.value)}
                    />
                  ) : (
                    <input
                      className="prompt-input"
                      style={{ width: '100%', padding: '0.55rem 0.8rem', fontSize: '0.88rem' }}
                      value={f.value}
                      onChange={(e) => handleFieldChange(i, e.target.value)}
                    />
                  )}
                </div>
              );
            })}
          </div>

          {/* Flagged Fields - User Input Required */}
          {flagged_fields && flagged_fields.length > 0 && (
            <div style={{ background: 'rgba(255, 152, 0, 0.08)', border: '1px solid rgba(255, 152, 0, 0.4)', padding: '0.86rem 1rem', borderRadius: '10px', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 600, marginBottom: '0.6rem', color: '#ff9800' }}>
                <Edit3 size={16} />
                <span>⚠ {flagged_fields.length} Fields Need Your Input:</span>
              </div>

              {flagged_fields.filter(f => !f.is_file).map((f, i) => (
                <div key={i} style={{ marginBottom: '0.8rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      {f.field_label}
                      {f.fieldType && f.fieldType !== 'text' && (
                        <span style={{ ...badgeStyle('#ff9800', 'rgba(255,152,0,0.15)'), marginLeft: '0.5rem' }}>{f.fieldType}</span>
                      )}
                    </div>
                    {/* Instant AI Answer Generator Button for Flagged Questions */}
                    <button
                      type="button"
                      onClick={() => handleGenerateFlaggedAI(i, f.field_label)}
                      disabled={generatingFieldIdx === `flag_${i}`}
                      style={{
                        background: 'rgba(127,0,255,0.15)',
                        border: '1px solid var(--accent-purple)',
                        color: 'var(--accent-purple)',
                        fontSize: '0.74rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.3rem',
                        fontWeight: 600
                      }}
                    >
                      <Sparkles size={11} />
                      {generatingFieldIdx === `flag_${i}` ? 'Generating...' : '✨ Generate with AI'}
                    </button>
                  </div>

                  {(f.fieldType === 'radio' || f.fieldType === 'dropdown') && f.options ? (
                    <select
                      value={userAnswers[i] || ''}
                      onChange={(e) => handleFlaggedChange(i, e.target.value)}
                      style={selectStyle}
                    >
                      <option value="">— Please select —</option>
                      {f.options.map((opt, oi) => (
                        <option key={oi} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : f.fieldType === 'checkbox' && f.options ? (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.3rem' }}>
                      {f.options.map((opt, oi) => {
                        const isChecked = Array.isArray(userAnswers[i]) && userAnswers[i].includes(opt);
                        return (
                          <label
                            key={oi}
                            style={{
                              display: 'flex', alignItems: 'center', gap: '0.3rem',
                              padding: '0.35rem 0.7rem', borderRadius: '6px', cursor: 'pointer',
                              fontSize: '0.84rem', fontWeight: 500,
                              background: isChecked ? 'rgba(0,230,118,0.15)' : 'rgba(255,255,255,0.04)',
                              border: isChecked ? '1px solid var(--accent-emerald)' : '1px solid var(--border-color)',
                              color: isChecked ? 'var(--accent-emerald)' : 'var(--text-muted)',
                              transition: 'all 0.15s ease'
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => handleCheckboxToggle(i, opt)}
                              style={{ accentColor: 'var(--accent-emerald)' }}
                            />
                            {opt}
                          </label>
                        );
                      })}
                    </div>
                  ) : (
                    <textarea
                      rows={2}
                      className="prompt-input"
                      placeholder={f.reason || 'Enter answer or click ✨ Generate with AI above...'}
                      value={userAnswers[i] || ''}
                      onChange={(e) => handleFlaggedChange(i, e.target.value)}
                      style={{ ...inputStyle, resize: 'vertical' }}
                    />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-actions" style={{ paddingTop: '0.6rem', borderTop: '1px solid var(--border-color)' }}>
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
