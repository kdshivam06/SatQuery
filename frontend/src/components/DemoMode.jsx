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

// ── Keyword → scenario routing table ─────────────────────────────────────────
// Maps keyword patterns to scenario IDs so the system can auto-select a model.
const KEYWORD_ROUTES = [
  { keywords: ['metadata', 'resolution', 'crs', 'band', 'coordinate', 'geotiff', 'projection', 'transform'],
    id: 'demo_metadata_reader' },
  { keywords: ['preview', 'thumbnail', 'rgb', 'visual', 'png', 'color', 'colour', 'true-colour'],
    id: 'demo_preview_generator' },
  { keywords: ['ndvi', 'vegetation', 'crop', 'plant', 'green', 'forest', 'agricultural', 'agriculture', 'health'],
    id: 'demo_ndvi' },
  { keywords: ['ndwi', 'water body', 'lake', 'reservoir', 'river', 'open water', 'pond'],
    id: 'demo_ndwi' },
  { keywords: ['mndwi', 'urban water', 'coastal', 'estuary', 'built-up water'],
    id: 'demo_mndwi' },
  { keywords: ['ndbi', 'built-up', 'impervious', 'urban extent', 'city', 'road', 'rooftop', 'infrastructure'],
    id: 'demo_ndbi' },
  { keywords: ['flood', 'sar water', 'inundation', 'monsoon', 'sentinel-1 water', 'flooded'],
    id: 'demo_sar_water' },
  { keywords: ['sar built', 'sar urban', 'backscatter', 'double bounce', 'vv vh', 'building structure'],
    id: 'demo_sar_builtup' },
  { keywords: ['change', 'before after', 'temporal', 'bi-temporal', 'difference', 'log ratio'],
    id: 'demo_change_map' },
  { keywords: ['mask fusion', 'wetland', 'combine mask', 'intersection', 'logical'],
    id: 'demo_mask_fusion' },
  { keywords: ['area', 'square kilometre', 'pixel count', 'hectare', 'extent measure'],
    id: 'demo_area_calculator' },
  { keywords: ['overlay', 'composite', 'alpha', 'visualize', 'visualise', 'highlight', 'layer'],
    id: 'demo_overlay' },
  { keywords: ['cross-modal', 'sar optical', 'dual encoder', 'matching', 'retrieval', 'cosine'],
    id: 'demo_dual_encoder' },
  { keywords: ['croma', 'contrastive', 'transformer feature', 'cls token', 'embedding'],
    id: 'demo_croma' },
  { keywords: ['remoteclip', 'text to image', 'text retrieval', 'find image', 'search scene'],
    id: 'demo_remoteclip' },
  { keywords: ['geochat', 'caption', 'land use', 'describe', 'vqa', 'scene description'],
    id: 'demo_geochat' },
  { keywords: ['rsllava', 'spectral characteristic', 'structural', 'multispectral analysis'],
    id: 'demo_rsllava' },
  { keywords: ['teochat', 'yearly change', 'annual change', 'compare image', 'year ago'],
    id: 'demo_teochat' },
  { keywords: ['segearth', 'segment', 'field boundary', 'parcel', 'delineate'],
    id: 'demo_segearth' },
  { keywords: ['sarclip', 'classify', 'zero-shot', 'port', 'airport', 'land class', 'sar class'],
    id: 'demo_sarclip' },
];

// Suggestion examples shown beneath the query box
const QUERY_SUGGESTIONS = [
  'Show vegetation health using NDVI across this agricultural scene',
  'Detect flooded areas in this Sentinel-1 SAR image',
  'Map urban built-up extent and impervious surfaces',
  'Describe this satellite image and identify land use categories',
  'Find water bodies using NDWI in this scene',
  'Match this SAR patch to an optical scene',
  'Calculate the flooded region area in km²',
];

/**
 * Pick the best scenario for a given query string.
 * Returns the matched scenario from the scenarios list, or null.
 */
function routeQuery(query, scenarios) {
  if (!query.trim() || !scenarios.length) return null;
  const lower = query.toLowerCase();

  // Score each route entry
  let bestScore = 0;
  let bestId = null;

  for (const route of KEYWORD_ROUTES) {
    let score = 0;
    for (const kw of route.keywords) {
      if (lower.includes(kw)) score += kw.split(' ').length; // longer phrases score higher
    }
    if (score > bestScore) {
      bestScore = score;
      bestId = route.id;
    }
  }

  if (!bestId) return null;
  return scenarios.find((s) => s.id === bestId) || null;
}

// ── Typing animation helper ───────────────────────────────────────────────────
function useTypewriter(text, speed = 18) {
  const [displayed, setDisplayed] = useState('');
  useEffect(() => {
    setDisplayed('');
    if (!text) return;
    let i = 0;
    const iv = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(iv);
    }, speed);
    return () => clearInterval(iv);
  }, [text, speed]);
  return displayed;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function DemoMode() {
  const [scenarios, setScenarios] = useState([]);
  const [query, setQuery] = useState('');
  const [routedScenario, setRoutedScenario] = useState(null);  // AI-selected model
  const [routing, setRouting] = useState(false);               // "AI is thinking" before route reveal
  const [running, setRunning] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [result, setResult] = useState(null);
  const [progress, setProgress] = useState(0);
  const timeoutsRef = useRef([]);
  const logEndRef = useRef(null);
  const inputRef = useRef(null);

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

  // ── Route then run ──────────────────────────────────────────────────────────
  const handleAnalyze = () => {
    if (!query.trim() || routing || running) return;

    // Reset state
    clearTimeouts();
    setRouting(true);
    setRoutedScenario(null);
    setAuditLog([]);
    setResult(null);
    setProgress(0);

    // Simulate a brief "AI routing" delay so it feels like intelligence is at work
    const routingDelay = 900 + Math.random() * 400;
    const tid = setTimeout(() => {
      const matched = routeQuery(query, scenarios);
      setRoutedScenario(matched || null);
      setRouting(false);

      if (matched) {
        // Short pause before execution starts
        const execTid = setTimeout(() => runScenario(matched), 500);
        timeoutsRef.current.push(execTid);
      }
    }, routingDelay);
    timeoutsRef.current.push(tid);
  };

  const runScenario = async (scenario) => {
    setRunning(true);
    setAuditLog([]);
    setResult(null);
    setProgress(0);

    const full = await fetch(apiPath(`/api/demo/scenarios/${scenario.id}`))
      .then((r) => r.json())
      .catch(() => null);

    if (!full) {
      setRunning(false);
      return;
    }

    const steps = full.audit_steps || [];
    const totalDuration = steps.length > 0 ? steps[steps.length - 1].delay : 4;

    steps.forEach((step, i) => {
      const tid = setTimeout(() => {
        setAuditLog((prev) => [...prev, step]);
        setProgress(((i + 1) / steps.length) * 100);
      }, step.delay * 1000);
      timeoutsRef.current.push(tid);
    });

    const finalTid = setTimeout(() => {
      setResult(full);
      setRunning(false);
    }, (totalDuration + 0.6) * 1000);
    timeoutsRef.current.push(finalTid);
  };

  const handleReset = () => {
    clearTimeouts();
    setRunning(false);
    setRouting(false);
    setRoutedScenario(null);
    setAuditLog([]);
    setResult(null);
    setProgress(0);
    setQuery('');
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleSuggestion = (s) => {
    setQuery(s);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAnalyze();
    }
  };

  const isIdle = !routing && !running && !result;

  return (
    <div className="demo-mode-container">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="demo-header">
        <div className="demo-header-left">
          <span className="demo-badge">⚡ SATQUERY ENGINE</span>
          <span className="demo-subtitle">
            Describe your analysis goal — the system will select and execute the optimal model
          </span>
        </div>
        {(routedScenario || result) && (
          <button className="demo-reset-btn" onClick={handleReset}>
            ← NEW QUERY
          </button>
        )}
      </div>

      {/* ── Query Input Panel ───────────────────────────────────────────── */}
      {isIdle && !routedScenario && (
        <div className="demo-query-input-panel">
          <div className="demo-panel-title">// ENTER ANALYSIS QUERY</div>
          <div className="demo-input-wrapper">
            <textarea
              ref={inputRef}
              className="demo-query-textarea"
              placeholder="e.g. Show vegetation health using NDVI across this agricultural scene…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={3}
            />
            <button
              className="demo-run-btn demo-analyze-btn"
              onClick={handleAnalyze}
              disabled={!query.trim()}
            >
              ▶ ANALYZE
            </button>
          </div>

          {/* Suggestions */}
          <div className="demo-suggestions">
            <span className="demo-suggestion-label">Try:</span>
            {QUERY_SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                className="demo-suggestion-chip"
                onClick={() => handleSuggestion(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── AI Routing Indicator ────────────────────────────────────────── */}
      {routing && (
        <div className="demo-routing-panel">
          <div className="demo-routing-inner">
            <span className="demo-routing-spinner" />
            <div>
              <div className="demo-routing-title">Routing query to optimal model…</div>
              <div className="demo-routing-query">"{query}"</div>
            </div>
          </div>
          <div className="demo-routing-steps">
            <RoutingStep label="Tokenising query" done />
            <RoutingStep label="Extracting intent signals" done />
            <RoutingStep label="Matching tool registry" active />
            <RoutingStep label="Selecting execution backend" />
          </div>
        </div>
      )}

      {/* ── Main layout (after routing) ─────────────────────────────────── */}
      {!routing && (routedScenario || running || result) && (
        <div className="demo-layout">
          {/* Left: selected model card */}
          <div className="demo-selector-panel">
            <div className="demo-panel-title">
              <span>// SELECTED MODEL</span>
              <span className="demo-ai-tag">AI ROUTED</span>
            </div>

            <div className="demo-routed-query-box">
              <div className="demo-routed-query-label">Query</div>
              <div className="demo-routed-query-text">"{query}"</div>
            </div>

            {routedScenario && (
              <div className="demo-routed-model-card">
                <div className="demo-scenario-model">{routedScenario.model}</div>
                <div className="demo-scenario-role">{routedScenario.role}</div>
                <div className="demo-routed-meta">
                  <span className="demo-meta-tag">TOOL: {routedScenario.tool}</span>
                  <span className="demo-meta-tag">WORKFLOW: {routedScenario.workflow}</span>
                </div>
              </div>
            )}
          </div>

          {/* Right: audit + result */}
          <div className="demo-right-panel">
            {/* Audit log */}
            {(running || auditLog.length > 0) && (
              <div className="demo-audit-panel">
                <div className="demo-panel-title">
                  <span>// WORKFLOW AUDIT LOG</span>
                  {running && <span className="demo-thinking-badge">● PROCESSING …</span>}
                </div>

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

                <button className="demo-run-btn demo-rerun-btn" onClick={handleReset}>
                  ← NEW QUERY
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Empty / unmatched state ─────────────────────────────────────── */}
      {!routing && !running && !result && !routedScenario && query && (
        <div className="demo-empty-state">
          <div className="demo-empty-icon">🔍</div>
          <p>No matching analysis model found for this query.</p>
          <p className="demo-empty-sub">Try rephrasing with keywords like "NDVI", "flood", "segment", "caption", etc.</p>
        </div>
      )}
    </div>
  );
}

// ── Helper: routing step indicator ────────────────────────────────────────────
function RoutingStep({ label, done, active }) {
  return (
    <div className={`demo-routing-step ${done ? 'done' : ''} ${active ? 'active' : ''}`}>
      <span className="demo-routing-step-dot">
        {done ? '✓' : active ? '○' : '·'}
      </span>
      <span>{label}</span>
    </div>
  );
}
