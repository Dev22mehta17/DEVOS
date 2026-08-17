import React, { useState, useEffect } from 'react';
import { Cpu, Send, Sparkles, Shield, Database } from 'lucide-react';
import StepStream from './components/StepStream';
import EmailPreviewModal from './components/EmailPreviewModal';
import FormReviewModal from './components/FormReviewModal';
import MemoryManager from './components/MemoryManager';

export default function App() {
  const [goal, setGoal] = useState('');
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingEmail, setPendingEmail] = useState(null);
  const [pendingForm, setPendingForm] = useState(null);
  const [profile, setProfile] = useState({});

  // 1. Listen to SSE live step stream
  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8000/api/stream');

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.step_type === 'HEARTBEAT') return;

        setLogs((prev) => [...prev, data]);

        if (data.step_type === 'APPROVAL_REQUIRED') {
          if (data.details && data.details.recipient) {
            setPendingEmail(data.details);
          } else if (data.details && data.details.filled_fields) {
            setPendingForm(data.details);
          }
          setIsProcessing(false);
        } else if (data.step_type === 'COMPLETED') {
          setIsProcessing(false);
        }
      } catch (err) {
        console.error('Error parsing SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE Error:', err);
    };

    return () => eventSource.close();
  }, []);

  // 2. Fetch profile memory on load
  useEffect(() => {
    fetch('http://localhost:8000/api/memory')
      .then((res) => res.json())
      .then((data) => setProfile(data))
      .catch((err) => console.error('Error loading memory:', err));
  }, []);

  const handleExecute = async (goalText) => {
    const targetGoal = goalText || goal;
    if (!targetGoal.trim()) return;

    setIsProcessing(true);
    setGoal(''); // Clear input box for next command
    setLogs((prev) => [
      ...prev,
      { step_type: 'THINKING', message: `User goal submitted: "${targetGoal}"` },
    ]);

    try {
      const res = await fetch('http://localhost:8000/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: targetGoal }),
      });
      const data = await res.json();
      console.log('Execute result:', data);
    } catch (err) {
      console.error('Execution error:', err);
      setIsProcessing(false);
    }
  };

  const handleApproveAction = async (actionId, approvalPayload) => {
    try {
      await fetch('http://localhost:8000/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, payload: approvalPayload }),
      });
      setPendingEmail(null);
      setPendingForm(null);
    } catch (err) {
      console.error('Approve error:', err);
    }
  };

  const handleRejectAction = async (actionId) => {
    try {
      await fetch('http://localhost:8000/api/reject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId }),
      });
      setPendingEmail(null);
      setPendingForm(null);
    } catch (err) {
      console.error('Reject error:', err);
    }
  };

  const handleSaveMemory = async (updatedData) => {
    try {
      const res = await fetch('http://localhost:8000/api/memory', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedData),
      });
      const data = await res.json();
      setProfile(data.data);
    } catch (err) {
      console.error('Save memory error:', err);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo-container">
          <div className="logo-icon">
            <Cpu color="#fff" size={22} />
          </div>
          <div>
            <div className="logo-title">JARVIS — DevOS</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              Personal Computer Agent • Chrome Browser & OS Control
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.82rem',
              color: 'var(--accent-cyan)',
              background: 'rgba(0,242,254,0.1)',
              padding: '0.4rem 0.8rem',
              borderRadius: '8px',
              border: '1px solid rgba(0,242,254,0.3)',
            }}
          >
            <Shield size={16} />
            <span>HITL Security Boundary Active</span>
          </div>

          <div className="status-badge">
            <div className="pulse-dot"></div>
            <span>Connected (Chrome CDP 9222)</span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="dashboard-grid">
        <div className="main-column">
          {/* Goal Entry Card */}
          <div className="glass-panel prompt-card">
            <div className="prompt-title">What would you like JARVIS to do on your Mac?</div>
            <div className="prompt-input-wrapper">
              <input
                className="prompt-input"
                placeholder="e.g. Open Mail and send an email to Dev on mehtadev2004@gmail.com..."
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
              />
              <button
                className="action-btn"
                onClick={() => handleExecute()}
                disabled={isProcessing}
              >
                <Sparkles size={18} /> Execute Goal
              </button>
            </div>

            {/* Quick Presets */}
            <div className="chips-row">
              <button
                className="chip-btn"
                onClick={() => {
                  setGoal("Send an email to mehtadev2004@gmail.com saying I'll be available tomorrow after 4 PM");
                }}
              >
                ✉️ Gmail: Send Email to mehtadev2004@gmail.com
              </button>
              <button
                className="chip-btn"
                onClick={() => {
                  setGoal("Fill job application form at https://<paste-form-url-here> with my profile and attach Dev_Resume.pdf");
                }}
              >
                📝 Form: Auto-fill Job Application (Paste URL)
              </button>
              <button
                className="chip-btn"
                onClick={() => {
                  setGoal("Find 5 SDE-1 remote jobs matching my Amazon intern profile and rank them");
                }}
              >
                🔍 Research: Search SDE-1 Remote Jobs
              </button>
            </div>
          </div>

          {/* Antigravity Step Feed */}
          <StepStream logs={logs} isProcessing={isProcessing} />
        </div>

        {/* Side Panel: Memory */}
        <div className="side-column">
          <MemoryManager profile={profile} onSave={handleSaveMemory} />
        </div>
      </div>

      {/* HITL Modals */}
      <EmailPreviewModal
        emailData={pendingEmail}
        onApprove={handleApproveAction}
        onReject={handleRejectAction}
      />
      <FormReviewModal
        formData={pendingForm}
        onApprove={handleApproveAction}
        onReject={handleRejectAction}
      />
    </div>
  );
}
