import React, { useState, useEffect } from 'react';
import { Cpu, Send, Sparkles, Shield, Database } from 'lucide-react';
import StepStream from './components/StepStream';
import EmailPreviewModal from './components/EmailPreviewModal';
import FormReviewModal from './components/FormReviewModal';
import MemoryManager from './components/MemoryManager';
import SearchAnswerCard from './components/SearchAnswerCard';
import ResearchDossierCard from './components/ResearchDossierCard';
import RecruiterQueueModal from './components/RecruiterQueueModal';
import CampaignPreviewModal from './components/CampaignPreviewModal';
import CampaignTrackerCard from './components/CampaignTrackerCard';

export default function App() {
  const [goal, setGoal] = useState('');
  const [logs, setLogs] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [pendingEmail, setPendingEmail] = useState(null);
  const [pendingForm, setPendingForm] = useState(null);
  const [searchResult, setSearchResult] = useState(null);
  const [dossierResult, setDossierResult] = useState(null);
  const [recruiterQueue, setRecruiterQueue] = useState(null);
  const [campaignPreview, setCampaignPreview] = useState(null);
  const [campaignTracker, setCampaignTracker] = useState(null);
  const [profile, setProfile] = useState({});

  // 1. Listen to SSE live step stream
  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8000/api/stream');

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.step_type === 'HEARTBEAT') return;

        setLogs((prev) => [...prev, data]);

        if (data.step_type === 'CAMPAIGN_PREVIEW') {
          if (data.details) {
            setCampaignPreview(data.details);
          }
          setIsProcessing(false);
        } else if (data.step_type === 'CAMPAIGN_PROGRESS') {
          if (data.details) {
            setCampaignTracker(data.details);
          }
        } else if (data.step_type === 'RESEARCH_DOSSIER') {
          if (data.details) {
            setDossierResult(data.details);
          }
          setIsProcessing(false);
        } else if (data.step_type === 'RECRUITER_QUEUE') {
          if (data.details) {
            setRecruiterQueue(data.details);
          }
          setIsProcessing(false);
        } else if (data.step_type === 'SEARCH_RESULT') {
          if (data.details) {
            setSearchResult(data.details);
          }
        } else if (data.step_type === 'APPROVAL_REQUIRED') {
          if (data.details && data.details.recipient) {
            setPendingEmail(data.details);
          } else if (data.details && data.details.filled_fields) {
            setPendingForm(data.details);
          }
          setIsProcessing(false);
        } else if (data.step_type === 'COMPLETED') {
          setIsProcessing(false);
          if (data.details && (data.details.direct_answer || data.details.sources)) {
            setSearchResult(data.details);
          } else if (data.details && data.details.comparison_matrix) {
            setDossierResult(data.details);
          }
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
    setSearchResult(null); // Clear previous search result card
    setDossierResult(null); // Clear previous dossier
    setRecruiterQueue(null); // Clear previous recruiter queue
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
      setCampaignPreview(null);
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
      setCampaignPreview(null);
    } catch (err) {
      console.error('Reject error:', err);
    }
  };

  const handleCancelCampaign = async (campaignId) => {
    try {
      await fetch(`http://localhost:8000/api/campaign/cancel/${campaignId}`, {
        method: 'POST',
      });
      setCampaignTracker((prev) => prev ? { ...prev, status: 'CANCELLED' } : null);
    } catch (err) {
      console.error('Cancel campaign error:', err);
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
            <div className="logo-title">DevOS</div>
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

      {/* Main Grid Layout */}
      <div className="app-main-grid">
        {/* Left Column: Command & Live Execution Feed */}
        <div className="main-column">
          {/* Goal Entry Card */}
          <div className="glass-panel prompt-card">
            <div className="prompt-title">What would you like DevOS to do on your Mac?</div>
            <div className="prompt-input-wrapper">
              <input
                className="prompt-input"
                placeholder="e.g. 'Send my intro to ananya@atlys.com (AI Engineer), rahul@microsoft.com (Backend)' or 'Compare Stripe vs Razorpay'"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleExecute();
                }}
                disabled={isProcessing}
              />
              <button
                className="prompt-btn"
                onClick={() => handleExecute()}
                disabled={isProcessing || !goal.trim()}
              >
                <Send size={16} />
              </button>
            </div>

            {/* Quick Action Preset Chips */}
            <div className="preset-chips-container">
              <button
                className="chip-btn"
                onClick={() => {
                  setGoal("Send my intro to ananya@atlys.com (AI Engineer at Atlys), rahul@microsoft.com (Backend SDE at Microsoft), priya@google.com (ML Engineer at Google) tomorrow at 10 AM");
                }}
              >
                📧 Campaign: "Bulk Recruiter Outreach (3 targets)"
              </button>
              <button
                className="chip-btn"
                onClick={() => {
                  setGoal("Research Stripe vs Razorpay pricing in India, compare their payout settlement times and UPI transaction fees, and create a comparison table for me");
                }}
              >
                🔬 Deep Research: "Stripe vs Razorpay Comparison"
              </button>
              <button
                className="chip-btn"
                onClick={() => {
                  setGoal("Check recruiter emails & triage my response queue");
                }}
              >
                📬 Proactive: "Recruiter Inbox Triage Queue"
              </button>
              <button
                className="chip-btn"
                onClick={() => {
                  setGoal("Fill out the job application form at https://<paste-url> with my resume");
                }}
              >
                📝 Form: Auto-fill Application
              </button>
            </div>
          </div>

          {/* Real-time Search Result & AI Answer Card */}
          <SearchAnswerCard
            searchResult={searchResult}
            onClose={() => setSearchResult(null)}
          />

          {/* Real-time Deep Research Dossier Card */}
          <ResearchDossierCard
            dossier={dossierResult}
            onClose={() => setDossierResult(null)}
          />

          {/* Real-time Campaign Delivery Tracker Card */}
          <CampaignTrackerCard
            campaignStatus={campaignTracker}
            onCancel={handleCancelCampaign}
            onClose={() => setCampaignTracker(null)}
          />

          {/* Antigravity Step Feed */}
          <StepStream logs={logs} isProcessing={isProcessing} />
        </div>

        {/* Side Panel: Memory */}
        <div className="side-column">
          <MemoryManager profile={profile} onSave={handleSaveMemory} />
        </div>
      </div>

      {/* HITL Modals */}
      <CampaignPreviewModal
        campaignData={campaignPreview}
        onApprove={handleApproveAction}
        onReject={handleRejectAction}
      />
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
      <RecruiterQueueModal
        queueData={recruiterQueue}
        onApproveItem={handleApproveAction}
        onApproveAll={() => setRecruiterQueue(null)}
        onClose={() => setRecruiterQueue(null)}
      />
    </div>
  );
}
