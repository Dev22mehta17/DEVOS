import React, { useState, useEffect } from 'react';
import { Send, Clock, CheckCircle2, AlertCircle, RefreshCw, XCircle, ChevronDown, ChevronUp, Mail } from 'lucide-react';

export default function CampaignTrackerCard({ campaignStatus, onCancel, onClose }) {
  if (!campaignStatus) return null;

  const {
    campaign_id,
    title = "Email Campaign",
    total = 0,
    sent = 0,
    failed = 0,
    pending = 0,
    sending = 0,
    cancelled = 0,
    status = "RUNNING",
    schedule_display = "Immediately",
    jobs = []
  } = campaignStatus;

  const [expanded, setExpanded] = useState(true);
  const [localStatus, setLocalStatus] = useState(campaignStatus);

  // Poll for campaign status every 8 seconds if campaign is active
  useEffect(() => {
    setLocalStatus(campaignStatus);

    if (status === 'COMPLETED' || status === 'CANCELLED') return;

    const interval = setInterval(() => {
      fetch(`http://localhost:8000/api/campaign/status/${campaign_id}`)
        .then((res) => res.json())
        .then((data) => {
          if (data && data.campaign_id) {
            setLocalStatus(data);
          }
        })
        .catch((err) => console.log('Polling status error:', err));
    }, 8000);

    return () => clearInterval(interval);
  }, [campaign_id, status]);

  const currentStatus = localStatus || campaignStatus;
  const progressPercent = currentStatus.total > 0 ? Math.round(((currentStatus.sent + currentStatus.failed) / currentStatus.total) * 100) : 0;

  const getJobStatusBadge = (jobStatus) => {
    switch (jobStatus) {
      case 'SENT':
        return <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(0,230,118,0.15)', color: 'var(--accent-emerald)', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}><CheckCircle2 size={11} /> Sent</span>;
      case 'SENDING':
        return <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(0,242,254,0.15)', color: 'var(--accent-cyan)', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}><RefreshCw size={11} className="spin" /> Sending...</span>;
      case 'RETRY':
        return <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(234,179,8,0.15)', color: '#facc15', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}><RefreshCw size={11} /> Retrying</span>;
      case 'FAILED':
        return <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,23,68,0.15)', color: 'var(--accent-rose)', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}><AlertCircle size={11} /> Failed</span>;
      case 'CANCELLED':
        return <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.08)', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}><XCircle size={11} /> Cancelled</span>;
      default:
        return <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', display: 'inline-flex', alignItems: 'center', gap: '0.2rem' }}><Clock size={11} /> Queued</span>;
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1rem', marginTop: '1rem', border: '1px solid rgba(0, 242, 254, 0.3)', borderRadius: '12px' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.8rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div style={{ background: 'rgba(0, 242, 254, 0.15)', padding: '0.4rem', borderRadius: '8px', display: 'flex' }}>
            <Mail size={18} color="var(--accent-cyan)" />
          </div>
          <div>
            <div style={{ fontSize: '0.92rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Campaign Tracker: {currentStatus.title}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Scheduled: {currentStatus.schedule_display} • {currentStatus.status}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', padding: '0.2rem' }}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          {onClose && (
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', padding: '0.2rem' }}
            >
              <XCircle size={16} />
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div style={{ marginBottom: '0.8rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '0.3rem', color: 'var(--text-dim)' }}>
          <span>Progress ({currentStatus.sent}/{currentStatus.total} sent)</span>
          <span style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>{progressPercent}%</span>
        </div>
        <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${progressPercent}%`,
              background: currentStatus.status === 'COMPLETED' ? 'var(--accent-emerald)' : 'linear-gradient(90deg, var(--accent-cyan), var(--accent-purple))',
              transition: 'width 0.4s ease'
            }}
          />
        </div>
      </div>

      {/* Status Counters */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.4rem', marginBottom: expanded ? '0.8rem' : '0' }}>
        <div style={{ background: 'rgba(0,230,118,0.06)', border: '1px solid rgba(0,230,118,0.15)', borderRadius: '6px', padding: '0.35rem 0.5rem', textAlign: 'center' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Sent</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-emerald)' }}>{currentStatus.sent}</div>
        </div>
        <div style={{ background: 'rgba(0,242,254,0.06)', border: '1px solid rgba(0,242,254,0.15)', borderRadius: '6px', padding: '0.35rem 0.5rem', textAlign: 'center' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Pending</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-cyan)' }}>{currentStatus.pending + currentStatus.sending}</div>
        </div>
        <div style={{ background: 'rgba(255,23,68,0.06)', border: '1px solid rgba(255,23,68,0.15)', borderRadius: '6px', padding: '0.35rem 0.5rem', textAlign: 'center' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Failed</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--accent-rose)' }}>{currentStatus.failed}</div>
        </div>
        <div style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '0.35rem 0.5rem', textAlign: 'center' }}>
          <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Total</div>
          <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)' }}>{currentStatus.total}</div>
        </div>
      </div>

      {/* Expanded Jobs List */}
      {expanded && currentStatus.jobs && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', maxHeight: '240px', overflowY: 'auto', paddingRight: '0.2rem' }}>
          {currentStatus.jobs.map((job, idx) => (
            <div
              key={job.job_id || idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.45rem 0.7rem',
                background: 'rgba(255,255,255,0.02)',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                fontSize: '0.78rem'
              }}
            >
              <div>
                <div style={{ fontWeight: 500, color: 'var(--text-main)' }}>
                  {job.name} • <span style={{ color: 'var(--accent-cyan)' }}>{job.company}</span>
                </div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                  {job.email} {job.error_message && <span style={{ color: 'var(--accent-rose)' }}>• {job.error_message}</span>}
                </div>
              </div>

              <div>{getJobStatusBadge(job.status)}</div>
            </div>
          ))}
        </div>
      )}

      {/* Action Footer */}
      {currentStatus.status !== 'COMPLETED' && currentStatus.status !== 'CANCELLED' && onCancel && (
        <div style={{ marginTop: '0.6rem', paddingTop: '0.6rem', borderTop: '1px solid var(--border-color)', display: 'flex', justifyContent: 'flex-end' }}>
          <button
            onClick={() => onCancel(currentStatus.campaign_id)}
            style={{
              background: 'rgba(255,23,68,0.1)',
              border: '1px solid rgba(255,23,68,0.3)',
              color: 'var(--accent-rose)',
              padding: '0.3rem 0.7rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              cursor: 'pointer'
            }}
          >
            Cancel Remaining
          </button>
        </div>
      )}
    </div>
  );
}
