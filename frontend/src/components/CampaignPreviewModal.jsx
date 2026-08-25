import React, { useState } from 'react';
import { Mail, Calendar, Clock, Paperclip, ChevronDown, ChevronUp, CheckCircle, Edit3, X, Send, Sparkles, User, Building, Briefcase } from 'lucide-react';

export default function CampaignPreviewModal({ campaignData, onApprove, onReject }) {
  if (!campaignData) return null;

  const {
    campaign_id,
    action_id,
    total_recipients,
    drafts: initialDrafts = [],
    schedule_time: initialScheduleTime,
    schedule_display,
    attach_resume,
    resume_filename
  } = campaignData;

  const [drafts, setDrafts] = useState(initialDrafts);
  const [expandedIndex, setExpandedIndex] = useState(0); // expand first by default
  const [scheduleTime, setScheduleTime] = useState(initialScheduleTime || '');
  const [sendImmediately, setSendImmediately] = useState(!initialScheduleTime);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleDraftChange = (index, field, value) => {
    const updated = [...drafts];
    updated[index] = { ...updated[index], [field]: value };
    setDrafts(updated);
  };

  const handleApprove = () => {
    if (isSubmitting) return;
    setIsSubmitting(true);

    const payload = {
      campaign_id,
      action_id: action_id || campaign_id,
      total_recipients: drafts.length,
      drafts,
      schedule_time: sendImmediately ? null : scheduleTime,
      schedule_display: sendImmediately
        ? "Immediately after approval"
        : (scheduleTime ? new Date(scheduleTime).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }) : "Immediately"),
      attach_resume
    };

    onApprove(action_id || campaign_id, payload);
  };

  const getProfileBadgeStyle = (profile) => {
    switch (profile) {
      case 'ml_ai':
        return { bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: 'rgba(168, 85, 247, 0.3)' };
      case 'backend':
        return { bg: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: 'rgba(59, 130, 246, 0.3)' };
      case 'frontend':
        return { bg: 'rgba(236, 72, 153, 0.15)', color: '#f472b6', border: 'rgba(236, 72, 153, 0.3)' };
      case 'devops_cloud':
        return { bg: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: 'rgba(234, 179, 8, 0.3)' };
      default:
        return { bg: 'rgba(0, 242, 254, 0.15)', color: 'var(--accent-cyan)', border: 'rgba(0, 242, 254, 0.3)' };
    }
  };

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-card" style={{ maxWidth: '820px', maxHeight: '88vh', display: 'flex', flexDirection: 'column' }}>
        
        {/* Header */}
        <div className="modal-header" style={{ flexShrink: 0, paddingBottom: '0.8rem', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)', padding: '0.5rem', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Mail size={22} color="#0a0c10" />
          </div>
          <div style={{ flex: 1 }}>
            <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <span>Email Campaign — Review & Personalization</span>
              <span style={{ fontSize: '0.72rem', background: 'rgba(0,242,254,0.15)', color: 'var(--accent-cyan)', padding: '2px 8px', borderRadius: '4px' }}>
                {drafts.length} Recipients
              </span>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
              Personalized outreach with role-specific technical skill matching & background scheduling
            </div>
          </div>
        </div>

        {/* Schedule & Attachment Bar */}
        <div style={{ flexShrink: 0, background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '0.7rem 1rem', margin: '0.8rem 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.8rem' }}>
          
          {/* Scheduling control */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.84rem', color: 'var(--text-main)' }}>
              <Clock size={15} color="var(--accent-cyan)" />
              <span style={{ fontWeight: 500 }}>Schedule:</span>
            </div>
            
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.82rem', cursor: 'pointer', color: sendImmediately ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
              <input
                type="radio"
                name="schedule_mode"
                checked={sendImmediately}
                onChange={() => setSendImmediately(true)}
              />
              Send Immediately
            </label>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.82rem', cursor: 'pointer', color: !sendImmediately ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
              <input
                type="radio"
                name="schedule_mode"
                checked={!sendImmediately}
                onChange={() => setSendImmediately(false)}
              />
              Pick Date & Time
            </label>

            {!sendImmediately && (
              <input
                type="datetime-local"
                className="prompt-input"
                style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem', width: 'auto' }}
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
              />
            )}
          </div>

          {/* Resume Attachment Badge */}
          {resume_filename && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--accent-emerald)', background: 'rgba(0,230,118,0.08)', padding: '0.25rem 0.6rem', borderRadius: '6px', border: '1px solid rgba(0,230,118,0.2)' }}>
              <Paperclip size={13} />
              <span>Resume attached: <strong>{resume_filename}</strong></span>
            </div>
          )}
        </div>

        {/* Scrollable Drafts List */}
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.3rem', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {drafts.map((d, idx) => {
            const isExpanded = expandedIndex === idx;
            const badge = getProfileBadgeStyle(d.skill_profile);

            return (
              <div
                key={idx}
                style={{
                  background: isExpanded ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.015)',
                  border: isExpanded ? '1px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                  borderRadius: '8px',
                  transition: 'all 0.2s ease',
                  overflow: 'hidden'
                }}
              >
                {/* Collapsed row header */}
                <div
                  onClick={() => setExpandedIndex(isExpanded ? -1 : idx)}
                  style={{
                    padding: '0.7rem 1rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    userSelect: 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', flex: 1 }}>
                    <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', fontWeight: 600 }}>
                      {idx + 1}
                    </div>
                    <div>
                      <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>{d.name}</span>
                        <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>•</span>
                        <span style={{ color: 'var(--accent-cyan)' }}>{d.company}</span>
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        {d.role} • <span style={{ fontFamily: 'var(--font-mono)' }}>{d.email}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', background: badge.bg, color: badge.color, border: `1px solid ${badge.border}`, fontWeight: 500 }}>
                      {d.skill_profile ? d.skill_profile.replace('_', '/').toUpperCase() : 'GENERAL SDE'}
                    </span>
                    {isExpanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
                  </div>
                </div>

                {/* Expanded edit drawer */}
                {isExpanded && (
                  <div style={{ padding: '0.8rem 1rem 1rem', borderTop: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
                      <div>
                        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.2rem', display: 'block' }}>Recipient Email:</label>
                        <input
                          className="prompt-input"
                          style={{ fontSize: '0.82rem', padding: '0.4rem 0.6rem' }}
                          value={d.email}
                          onChange={(e) => handleDraftChange(idx, 'email', e.target.value)}
                        />
                      </div>
                      <div>
                        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.2rem', display: 'block' }}>Subject Line:</label>
                        <input
                          className="prompt-input"
                          style={{ fontSize: '0.82rem', padding: '0.4rem 0.6rem' }}
                          value={d.subject}
                          onChange={(e) => handleDraftChange(idx, 'subject', e.target.value)}
                        />
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                        <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                          <Edit3 size={12} /> Email Body (deterministic template + skill lines):
                        </label>
                        <span style={{ fontSize: '0.72rem', color: 'var(--accent-emerald)' }}>
                          ✨ Skills: {d.relevant_skills || 'C++, Python, DSA'}
                        </span>
                      </div>
                      <textarea
                        className="prompt-input"
                        rows={7}
                        value={d.body}
                        onChange={(e) => handleDraftChange(idx, 'body', e.target.value)}
                        style={{
                          fontSize: '0.82rem',
                          padding: '0.6rem',
                          fontFamily: 'var(--font-body)',
                          lineHeight: 1.5,
                          resize: 'vertical'
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div style={{ flexShrink: 0, marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Sparkles size={14} color="var(--accent-cyan)" />
            <span>Emails will be sent with 15s safety intervals & automatic retry on failure.</span>
          </div>

          <div style={{ display: 'flex', gap: '0.6rem' }}>
            <button
              className="btn-secondary"
              onClick={() => onReject(action_id || campaign_id)}
              disabled={isSubmitting}
              style={{ fontSize: '0.85rem', padding: '0.5rem 1rem' }}
            >
              <X size={14} style={{ marginRight: '0.3rem' }} /> Cancel
            </button>
            <button
              className="btn-primary"
              onClick={handleApprove}
              disabled={isSubmitting || drafts.length === 0}
              style={{ fontSize: '0.85rem', padding: '0.5rem 1.2rem' }}
            >
              <Send size={14} style={{ marginRight: '0.3rem' }} />
              {isSubmitting
                ? 'Queueing Campaign...'
                : sendImmediately
                ? `Approve & Send ${drafts.length} Emails Now`
                : `Approve & Schedule for ${scheduleTime ? new Date(scheduleTime).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'Date'}`}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
