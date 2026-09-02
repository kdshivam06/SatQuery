import React, { useState, useEffect, useRef } from 'react';
import '../styles/demo.css';

const API =
  import.meta.env.VITE_API_BASE ||
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : '');

const apiPath = (p) => `${API}${p}`;

const STEP_ICONS = {
  router: '🧠',
  routing: '🔀',
  execute: '⚙️',
  fusion: '🔬',
  complete: '✅',
};

const STEP_COLORS = {
  router: '#a78bfa',
  routing: '#60a5fa',
  execute: '#34d399',
  fusion: '#fbbf24',
  complete: '#4ade80',
};

export default function DemoMode() {
  const [scenarios, setScenarios] = useState([]);
  const [selected, setSelected] = useState(null);
  const [running, setRunning] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [result, setResult] = useState(null);
  const [progress, setProgress] = useState(0);
  const timeoutsRef = useRef([]);
  const logEndRef = useRef(null);

  // Fetch scenario list on mount
  useEffect(() => {
    fetch(apiPath('/api/demo/scenarios'))
      .then((r) => r.json())
      .then((d) => setScenarios(d.scenarios || []))
      .catch(() => {});
  }, []);

  // Auto-scroll audit log
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [auditLog]);

  const clearTimeouts = () => {
    timeoutsRef.current.forEach(clearTimeout);
    timeoutsRef.current = [];
  };

  const runDemo = async (scenario) => {
    clearTimeouts();
    setRunning(true);
    setAuditLog([]);
    setResult(null);
    setProgress(0);

    // Fetch full scenario from backend
    const full = await fetch(apiPath(`/api/demo/scenarios/${scenario.id}`))
      .then((r) => r.json())
      .catch(() => null);

    if (!full) {
      setRunning(false);
      return;
    }

    const steps = full.audit_steps || [];
    const totalDuration = steps.length > 0 ? steps[steps.length - 1].delay : 4;

    // Schedule each audit step with its delay
    steps.forEach((step, i) => {
      const tid = setTimeout(() => {
        setAuditLog((prev) => [...prev, step]);
        setProgress(((i + 1) / steps.length) * 100);
      }, step.delay * 1000);
      timeoutsRef.current.push(tid);
    });

    // Show result after last step
    const finalTid = setTimeout(() => {
      setResult(full);
      setRunning(false);
    }, (totalDuration + 0.6) * 1000);
    timeoutsRef.current.push(finalTid);
  };

  const handleSelect = (scenario) => {
    if (running) return;
    setSelected(scenario);
    setAuditLog([]);
    setResult(null);
    setProgress(0);
  };

  const handleRun = () => {
    if (!selected || running) return;
    runDemo(selected);
  };

  const handleReset = () => {
    clearTimeouts();
    setRunning(false);
    setAuditLog([]);
    setResult(null);
    setProgress(0);
    setSelected(null);
  };

  return (
    <div className="demo-mode-container">
      {/* Header */}
      <div className="demo-header">
        <div className="demo-header-left">
          <span className="demo-badge">DEMO MODE</span>
          <span className="demo-subtitle">Select a model scenario to run a simulated AI audit</span>
        </div>
        {(selected || result) && (
          <button className="demo-reset-btn" onClick={handleReset}>
            ← RESET
          </button>
        )}
      </div>

      <div className="demo-layout">
        {/* Scenario Selector */}
        <div className="demo-selector-panel">
          <div className="demo-panel-title">
            <span>// TOOL SCENARIOS</span>
            <span className="demo-count">{scenarios.length} models</span>
          </div>
          <div className="demo-scenario-list">
            {scenarios.map((s) => (
              <div
                key={s.id}
                className={`demo-scenario-item ${selected?.id === s.id ? 'active' : ''}`}
                onClick={() => handleSelect(s)}
              >
                <div className="demo-scenario-model">{s.model}</div>
                <div className="demo-scenario-role">{s.role}</div>
                <div className="demo-scenario-query">"{s.query}"</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel */}
        <div className="demo-right-panel">
          {/* Selected query display */}
          {selected && !running && !result && (
            <div className="demo-query-preview">
              <div className="demo-panel-title">// SELECTED SCENARIO</div>
              <div className="demo-selected-model">{selected.model}</div>
              <div className="demo-selected-role">{selected.role}</div>
              <div className="demo-selected-query">"{selected.query}"</div>
              <button className="demo-run-btn" onClick={handleRun}>
                ▶ RUN DEMO ANALYSIS
              </button>
            </div>
          )}

          {/* Audit log stream */}
          {(running || auditLog.length > 0) && (
            <div className="demo-audit-panel">
              <div className="demo-panel-title">
                <span>// WORKFLOW AUDIT LOG</span>
                {running && <span className="demo-thinking-badge">● AI THINKING …</span>}
              </div>

              {/* Progress bar */}
              <div className="demo-progress-bar">
                <div
                  className="demo-progress-fill"
                  style={{ width: `${progress}%`, transition: 'width 0.5s ease' }}
                />
              </div>

              <div className="demo-audit-log">
                {auditLog.map((entry, i) => (
                  <div key={i} className="demo-audit-line" style={{ animationDelay: `${i * 0.05}s` }}>
                    <span className="demo-audit-time">[{entry.delay.toFixed(1)}s]</span>
                    <span
                      className="demo-audit-step"
                      style={{ color: STEP_COLORS[entry.step] || '#9ca3af' }}
                    >
                      {STEP_ICONS[entry.step] || '·'} {entry.step.toUpperCase()}
                    </span>
                    <span className="demo-audit-msg">{entry.msg}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>
          )}

          {/* Final result */}
          {result && !running && (
            <div className="demo-result-panel">
              <div className="demo-panel-title">
                <span>// ANALYSIS RESULT</span>
                <span className="demo-confidence-badge">
                  {Math.round(result.confidence * 100)}% CONFIDENCE
                </span>
              </div>

              <div className="demo-result-meta">
                <span className="demo-meta-tag">MODEL: {result.model}</span>
                <span className="demo-meta-tag">WORKFLOW: {result.workflow}</span>
                <span className="demo-meta-tag">TOOL: {result.tool}</span>
              </div>

              <div className="demo-answer-box">
                {result.answer.split('\n').map((line, i) =>
                  line.trim() === '' ? (
                    <br key={i} />
                  ) : (
                    <p key={i} className={line.startsWith('•') || line.match(/^\d\./) ? 'demo-bullet' : ''}>
                      {line}
                    </p>
                  )
                )}
              </div>

              {result.evidence && result.evidence.length > 0 && (
                <div className="demo-evidence-section">
                  <div className="demo-evidence-title">// EVIDENCE</div>
                  {result.evidence.map((e, i) => (
                    <div key={i} className="demo-evidence-item">
                      <span className="demo-evidence-dot">◆</span> {e}
                    </div>
                  ))}
                </div>
              )}

              <button className="demo-run-btn demo-rerun-btn" onClick={handleRun}>
                ↺ RE-RUN
              </button>
            </div>
          )}

          {/* Empty state */}
          {!selected && !running && !result && (
            <div className="demo-empty-state">
              <div className="demo-empty-icon">🛰️</div>
              <p>Select a model scenario from the left panel to begin a simulated AI analysis audit.</p>
              <p className="demo-empty-sub">Each scenario demonstrates the tool's purpose with a realistic query and live workflow trace.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
