import React, { useState, useEffect } from 'react';
import { Database, User, Briefcase, GraduationCap, Link as LinkIcon, Save, FileUp, Sparkles, FileText } from 'lucide-react';

export default function MemoryManager({ profile, onSave }) {
  const [memoryData, setMemoryData] = useState(profile || {});
  const [savedStatus, setSavedStatus] = useState('');
  const [uploadStatus, setUploadStatus] = useState('');

  useEffect(() => {
    setMemoryData(profile || {});
  }, [profile]);

  const handleChange = (section, key, value) => {
    setMemoryData(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploadStatus(`Ingesting '${file.name}'...`);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/memory/upload', {
        method: 'POST',
        body: formData
      });
      const result = await res.json();
      if (result.status === 'SUCCESS') {
        setUploadStatus(`✓ Ingested ${result.extracted_chars} chars from '${file.name}'!`);
        if (result.data) setMemoryData(result.data);
        setTimeout(() => setUploadStatus(''), 4000);
      }
    } catch (err) {
      console.error('File upload error:', err);
      setUploadStatus('Upload failed.');
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(memoryData);
    setSavedStatus('Memory updated successfully!');
    setTimeout(() => setSavedStatus(''), 3000);
  };

  return (
    <div className="glass-panel" style={{ padding: '1.2rem', maxHeight: '85vh', overflowY: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem', paddingBottom: '0.6rem', borderBottom: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '1.05rem' }}>
          <Database size={18} color="#7f00ff" />
          <span>User Memory Subsystem</span>
        </div>
        {savedStatus && (
          <span style={{ fontSize: '0.78rem', color: 'var(--accent-emerald)', fontWeight: 600 }}>{savedStatus}</span>
        )}
      </div>

      {/* Document Upload Button */}
      <div style={{ background: 'rgba(127,0,255,0.08)', border: '1px dashed var(--accent-purple)', padding: '0.8rem', borderRadius: '10px', marginBottom: '1rem', textAlign: 'center' }}>
        <label style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.3rem', color: 'var(--accent-purple)', fontWeight: 600, fontSize: '0.82rem' }}>
          <FileUp size={18} />
          <span>Ingest Resume / Document to Vector Memory</span>
          <input type="file" accept=".pdf,.txt,.doc,.docx" onChange={handleFileUpload} style={{ display: 'none' }} />
        </label>
        {uploadStatus && (
          <div style={{ fontSize: '0.76rem', color: 'var(--accent-emerald)', marginTop: '0.3rem', fontWeight: 500 }}>
            {uploadStatus}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem', fontSize: '0.86rem' }}>
        {/* Personal Details */}
        <div>
          <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
            <User size={15} /> Personal Details
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.35rem' }}
            value={memoryData.personal?.full_name || ''}
            onChange={(e) => handleChange('personal', 'full_name', e.target.value)}
            placeholder="Full Name"
          />
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.35rem' }}
            value={memoryData.personal?.email_primary || ''}
            onChange={(e) => handleChange('personal', 'email_primary', e.target.value)}
            placeholder="Primary Email"
          />
          <input
            className="prompt-input"
            style={{ width: '100%' }}
            value={memoryData.personal?.phone || ''}
            onChange={(e) => handleChange('personal', 'phone', e.target.value)}
            placeholder="Phone Number (e.g. +91-7206049507)"
          />
        </div>

        {/* Education & Experience */}
        <div>
          <div style={{ color: 'var(--accent-purple)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
            <GraduationCap size={15} /> Education & Academic Scores
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.35rem' }}
            value={memoryData.education?.university || ''}
            onChange={(e) => handleChange('education', 'university', e.target.value)}
            placeholder="University / College"
          />
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.35rem' }}
            value={memoryData.education?.degree || ''}
            onChange={(e) => handleChange('education', 'degree', e.target.value)}
            placeholder="Degree (e.g. B.E. Computer Engineering)"
          />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem', marginBottom: '0.35rem' }}>
            <input
              className="prompt-input"
              value={memoryData.education?.gpa || memoryData.education?.cgpa || ''}
              onChange={(e) => {
                handleChange('education', 'gpa', e.target.value);
                handleChange('education', 'cgpa', e.target.value);
              }}
              placeholder="Graduation CGPA (8.7)"
            />
            <input
              className="prompt-input"
              value={memoryData.education?.graduation_year || ''}
              onChange={(e) => handleChange('education', 'graduation_year', e.target.value)}
              placeholder="Passing Year (2026)"
            />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem', marginBottom: '0.35rem' }}>
            <input
              className="prompt-input"
              value={memoryData.education?.tenth_percentage || ''}
              onChange={(e) => handleChange('education', 'tenth_percentage', e.target.value)}
              placeholder="10th % (93.8)"
            />
            <input
              className="prompt-input"
              value={memoryData.education?.twelfth_percentage || ''}
              onChange={(e) => handleChange('education', 'twelfth_percentage', e.target.value)}
              placeholder="12th % (93.6)"
            />
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%' }}
            value={memoryData.professional?.current_role || ''}
            onChange={(e) => handleChange('professional', 'current_role', e.target.value)}
            placeholder="Current Role / Experience (e.g. SDE Intern at Amazon)"
          />
        </div>

        {/* Extra Context & Career Notes */}
        <div>
          <div style={{ color: 'var(--accent-emerald)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
            <Sparkles size={15} /> Extra Career Context & Notes (for AI answers)
          </div>
          <textarea
            className="prompt-input"
            rows={3}
            style={{ width: '100%', resize: 'vertical', fontSize: '0.84rem', lineHeight: 1.4, marginBottom: '0.35rem' }}
            value={memoryData.extra_context?.career_narrative || ''}
            onChange={(e) => handleChange('extra_context', 'career_narrative', e.target.value)}
            placeholder="Career narrative / background summary..."
          />
          <textarea
            className="prompt-input"
            rows={2}
            style={{ width: '100%', resize: 'vertical', fontSize: '0.84rem', lineHeight: 1.4 }}
            value={memoryData.extra_context?.custom_user_notes || ''}
            onChange={(e) => handleChange('extra_context', 'custom_user_notes', e.target.value)}
            placeholder="Extra notes (e.g. target roles, leadership stories, work style)..."
          />
        </div>

        {/* Social Links */}
        <div>
          <div style={{ color: 'var(--accent-amber)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.3rem' }}>
            <LinkIcon size={15} /> Social Links & Portfolio
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.35rem' }}
            value={memoryData.links?.github || ''}
            onChange={(e) => handleChange('links', 'github', e.target.value)}
            placeholder="GitHub URL (e.g. https://github.com/Dev22mehta17)"
          />
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.35rem' }}
            value={memoryData.links?.linkedin || ''}
            onChange={(e) => handleChange('links', 'linkedin', e.target.value)}
            placeholder="LinkedIn URL"
          />
          <input
            className="prompt-input"
            style={{ width: '100%' }}
            value={memoryData.links?.portfolio || ''}
            onChange={(e) => handleChange('links', 'portfolio', e.target.value)}
            placeholder="Portfolio / Website URL (e.g. https://devmehta.dev)"
          />
        </div>

        <button type="submit" className="action-btn" style={{ width: '100%', justifyContent: 'center', marginTop: '0.4rem', padding: '0.65rem' }}>
          <Save size={15} /> Save Memory Context
        </button>
      </form>
    </div>
  );
}
