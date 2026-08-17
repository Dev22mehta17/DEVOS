import React, { useState, useEffect } from 'react';
import { Database, User, Briefcase, GraduationCap, Link as LinkIcon, Save, FileUp, CheckCircle } from 'lucide-react';

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
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.2rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)', fontWeight: 600, fontSize: '1.1rem' }}>
          <Database size={20} color="#7f00ff" />
          <span>User Memory Subsystem</span>
        </div>
        {savedStatus && (
          <span style={{ fontSize: '0.8rem', color: 'var(--accent-emerald)', fontWeight: 600 }}>{savedStatus}</span>
        )}
      </div>

      {/* Document Upload Button */}
      <div style={{ background: 'rgba(127,0,255,0.08)', border: '1px dashed var(--accent-purple)', padding: '0.9rem', borderRadius: '10px', marginBottom: '1.2rem', textAlign: 'center' }}>
        <label style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem', color: 'var(--accent-purple)', fontWeight: 600, fontSize: '0.85rem' }}>
          <FileUp size={20} />
          <span>Ingest Resume / Doc to Context</span>
          <input type="file" accept=".pdf,.txt,.doc,.docx" onChange={handleFileUpload} style={{ display: 'none' }} />
        </label>
        {uploadStatus && (
          <div style={{ fontSize: '0.78rem', color: 'var(--accent-emerald)', marginTop: '0.4rem', fontWeight: 500 }}>
            {uploadStatus}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.88rem' }}>
        {/* Personal Details */}
        <div>
          <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
            <User size={16} /> Personal Details
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.4rem' }}
            value={memoryData.personal?.full_name || ''}
            onChange={(e) => handleChange('personal', 'full_name', e.target.value)}
            placeholder="Full Name"
          />
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.4rem' }}
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
          <div style={{ color: 'var(--accent-purple)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
            <GraduationCap size={16} /> Education & Experience
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.4rem' }}
            value={memoryData.education?.university || ''}
            onChange={(e) => handleChange('education', 'university', e.target.value)}
            placeholder="University / College"
          />
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.4rem' }}
            value={memoryData.education?.degree || ''}
            onChange={(e) => handleChange('education', 'degree', e.target.value)}
            placeholder="Degree"
          />
          <input
            className="prompt-input"
            style={{ width: '100%' }}
            value={memoryData.professional?.current_role || ''}
            onChange={(e) => handleChange('professional', 'current_role', e.target.value)}
            placeholder="Current Role / Experience (e.g. SDE Intern at Amazon)"
          />
        </div>

        {/* Social Links */}
        <div>
          <div style={{ color: 'var(--accent-amber)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
            <LinkIcon size={16} /> Social Links
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.4rem' }}
            value={memoryData.links?.github || ''}
            onChange={(e) => handleChange('links', 'github', e.target.value)}
            placeholder="GitHub URL (e.g. https://github.com/Dev22mehta17)"
          />
          <input
            className="prompt-input"
            style={{ width: '100%' }}
            value={memoryData.links?.linkedin || ''}
            onChange={(e) => handleChange('links', 'linkedin', e.target.value)}
            placeholder="LinkedIn URL (e.g. https://linkedin.com/in/DevMehta)"
          />
        </div>

        <button type="submit" className="action-btn" style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem', padding: '0.7rem' }}>
          <Save size={16} /> Save Memory Context
        </button>
      </form>
    </div>
  );
}
