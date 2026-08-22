import React, { useEffect, useRef } from 'react';
import { Activity, Terminal, ShieldAlert } from 'lucide-react';

export default function StepStream({ logs, isProcessing }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="glass-panel stream-card">
      <div className="stream-header">
        <div className="stream-title">
          <Terminal size={20} color="#00f2fe" />
          <span>DevOS Thinking & Live Feed</span>
        </div>
        {isProcessing && (
          <div className="status-badge">
            <div className="pulse-dot"></div>
            <span>Agent Active</span>
          </div>
        )}
      </div>

      <div className="stream-logs-container" ref={scrollRef}>
        {logs.length === 0 ? (
          <div style={{ color: 'var(--text-dim)', textAlign: 'center', padding: '3rem' }}>
            <Activity size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
            <p>Agent is idle. Enter a prompt or select a preset task to see real-time steps.</p>
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className={`log-item log-${log.step_type}`}>
              <span className={`badge badge-${log.step_type}`}>
                {log.step_type}
              </span>
              <div className="log-msg">
                {log.message}
                {log.details && log.details.direct_answer && (
                  <div
                    style={{
                      background: 'rgba(0, 242, 254, 0.08)',
                      border: '1px solid rgba(0, 242, 254, 0.25)',
                      borderRadius: '6px',
                      padding: '0.4rem 0.6rem',
                      marginTop: '0.35rem',
                      fontSize: '0.84rem',
                      color: '#f0f6fc',
                      lineHeight: 1.4
                    }}
                  >
                    💡 <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>Answer:</span> {log.details.direct_answer}
                  </div>
                )}
                {log.details && log.details.url && !log.details.direct_answer && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)', marginTop: '0.2rem' }}>
                    URL: {log.details.url}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
