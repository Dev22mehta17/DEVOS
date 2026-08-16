import React, { useState, useEffect } from 'react';
import { Database, User, Briefcase, GraduationCap, Link as LinkIcon, Save } from 'lucide-react';

export default function MemoryManager({ profile, onSave }) {
  const [memoryData, setMemoryData] = useState(profile || {});
  const [savedStatus, setSavedStatus] = useState('');

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

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.88rem' }}>
        {/* Personal */}
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
            style={{ width: '100%' }}
            value={memoryData.personal?.email_primary || ''}
            onChange={(e) => handleChange('personal', 'email_primary', e.target.value)}
            placeholder="Primary Email"
          />
        </div>

        {/* Education */}
        <div>
          <div style={{ color: 'var(--accent-purple)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
            <GraduationCap size={16} /> Education
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
            style={{ width: '100%' }}
            value={memoryData.education?.degree || ''}
            onChange={(e) => handleChange('education', 'degree', e.target.value)}
            placeholder="Degree"
          />
        </div>

        {/* Links */}
        <div>
          <div style={{ color: 'var(--accent-amber)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
            <LinkIcon size={16} /> Social Links
          </div>
          <input
            className="prompt-input"
            style={{ width: '100%', marginBottom: '0.4rem' }}
            value={memoryData.links?.github || ''}
            onChange={(e) => handleChange('links', 'github', e.target.value)}
            placeholder="GitHub URL"
          />
          <input
            className="prompt-input"
            style={{ width: '100%' }}
            value={memoryData.links?.linkedin || ''}
            onChange={(e) => handleChange('links', 'linkedin', e.target.value)}
            placeholder="LinkedIn URL"
          />
        </div>

        <button type="submit" className="action-btn" style={{ width: '100%', justifyContent: 'center', marginTop: '0.5rem', padding: '0.7rem' }}>
          <Save size={16} /> Save Memory Context
        </button>
      </form>
    </div>
  );
}
