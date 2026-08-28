import React, { useState, useEffect, useRef } from 'react';
import HollowGlobe from '../components/HollowGlobe';
import '../styles/hero.css';

const API =
  import.meta.env.VITE_API_BASE ||
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : '');

const apiPath = (path) => `${API}${path}`;

const resolveVisualUrl = (runId, rawUrl = '') => {
  if (!rawUrl) return '';
  if (/^https?:\/\//i.test(rawUrl)) return rawUrl;
  const cleaned = rawUrl.replace(/\\/g, '/');
  if (cleaned.startsWith('/api/') || cleaned.startsWith('/files/')) {
    return apiPath(cleaned);
  }

  let relative = cleaned.replace(/^\/+/, '');
  const lower = relative.toLowerCase();
  const fullMarker = `runs/api/${runId.toLowerCase()}/`;
  const fullMarkerIndex = lower.indexOf(fullMarker);
  if (fullMarkerIndex >= 0) {
    relative = relative.slice(fullMarkerIndex + fullMarker.length);
  } else {
    const runMarker = `${runId.toLowerCase()}/`;
    const runMarkerIndex = lower.indexOf(runMarker);
    if (runMarkerIndex >= 0) {
      relative = relative.slice(runMarkerIndex + runMarker.length);
    }
  }

  return apiPath(`/files/${runId}/${relative.replace(/^\/+/, '')}`);
};

const Hero = ({ isPreloaded = true }) => {
  // State
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [query, setQuery] = useState('');
  const [currentMode, setCurrentMode] = useState('auto');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentRunId, setCurrentRunId] = useState(null);
  const [runData, setRunData] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);
  const [health, setHealth] = useState({
    status: 'connecting...',
    routerMode: '–',
    toolsEnabled: '–',
    color: '#94a3b8'
  });
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef(null);
  const pollTimerRef = useRef(null);

  // 1. Health check
  const fetchHealth = () => {
    fetch(apiPath('/health'))
      .then((r) => r.json())
      .then((d) => {
        setHealth({
          status: 'online',
          routerMode: d.router_mode || '–',
          toolsEnabled: d.tools_enabled || 0,
          color: '#4ade80'
        });
      })
      .catch(() => {
        setHealth({
          status: 'offline',
          routerMode: '–',
          toolsEnabled: '–',
          color: '#f87171'
        });
      });
  };

  // 2. Fetch Recent Runs
  const fetchRecentRuns = () => {
    fetch(apiPath('/api/runs?limit=5'))
      .then((r) => r.json())
      .then((d) => {
        setRecentRuns(d.runs || []);
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetchHealth();
    fetchRecentRuns();

    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  // Polling logic
  const pollRun = async (runId) => {
    try {
      const res = await fetch(apiPath(`/api/runs/${runId}`));
      const data = await res.json();
      setRunData(data);
      if (data.status === 'completed' || data.status === 'failed') {
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        fetchRecentRuns();
      }
    } catch (err) {
      console.error('Error polling run:', err);
    }
  };

  const startPolling = (runId) => {
    setCurrentRunId(runId);
    setRunData({ run_id: runId, status: 'queued', progress: 0.05 });
    if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    pollTimerRef.current = setInterval(() => pollRun(runId), 1500);
    pollRun(runId);
  };

  const loadRun = async (runId) => {
    setCurrentRunId(runId);
    try {
      const res = await fetch(apiPath(`/api/runs/${runId}`));
      const data = await res.json();
      setRunData(data);
      if (data.status !== 'completed' && data.status !== 'failed') {
        startPolling(runId);
      }
    } catch (err) {
      alert('Failed to load run: ' + err.message);
    }
  };

  // File Handlers
  const handleAddFiles = (files) => {
    const newFiles = Array.from(files);
    setSelectedFiles((prev) => [...prev, ...newFiles]);
  };

  const handleRemoveFile = (index) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleAddFiles(e.dataTransfer.files);
    }
  };

  // Submit Analysis
  const handleSubmitAnalysis = async () => {
    if (!query.trim()) {
      alert('Please enter a query.');
      return;
    }
    if (!selectedFiles.length) {
      alert('Please upload at least one image.');
      return;
    }

    setIsSubmitting(true);
    const fd = new FormData();
    fd.append('query', query.trim());
    fd.append('mode', currentMode);
    selectedFiles.forEach((f) => fd.append('files', f));

    try {
      const res = await fetch(apiPath('/api/analyze'), { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Analysis failed');
      setIsSubmitting(false);
      startPolling(data.run_id);
    } catch (err) {
      setIsSubmitting(false);
      alert('Error: ' + err.message);
    }
  };

  // Demo selection
  const handleSetDemo = (demoQuery, mode) => {
    setQuery(demoQuery);
    setCurrentMode(mode);
  };

  return (
    <div className={`hero ${!isPreloaded ? 'hero-revealed' : ''}`}>
      <div className="preloader-revealer"></div>

      {/* HollowGlobe background container positioned on the right edge */}
      <div className="globe-right-container">
        <HollowGlobe />
      </div>

      {/* Sticky Top Header Navigation */}
      <header className="hero-header sticky-header">
        <div className="hero-title">
          <div className="hero-title-line">
            <span className="hero-title-word">SATQUERY</span>
          </div>
        </div>

        <div className="header-status-tags">
          <span className="status-tag" style={{ color: health.color }}>
            ● {health.status}
          </span>
          <span className="status-tag">router: {health.routerMode}</span>
          <span className="status-tag">tools: {health.toolsEnabled}</span>
        </div>

        <nav className="hero-nav">
          <a href="#workspace" className="nav-link">
            WORKSPACE
          </a>
          <a href="#logs" className="nav-link">
            LOGS
          </a>
          <a href="#guide" className="nav-link">
            GUIDE
          </a>
        </nav>
      </header>

      {/* Main Scrollable Content Container (Left Side Placement) */}
      <div className="hero-dashboard-content">
        <div className="left-side-containers">
          {/* Upload Panel */}
          <div className="panel dropzone-panel" id="workspace">
            <div className="panel-header">
              <span className="panel-title">// UPLOAD IMAGES</span>
              <span className="panel-badge">GEOTIFF / PATCHES</span>
            </div>

            <div
              className={`dropzone-box ${isDragOver ? 'dragging' : ''} ${selectedFiles.length > 0 ? 'has-file' : ''}`}
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
            >
              <div className="dropzone-text">
                <p className="drop-prompt">Drop satellite images here or click to browse</p>
                <p className="drop-subtext">GeoTIFF, .npy patches, .tif, .png, .jpg</p>
              </div>
              <input
                type="file"
                ref={fileInputRef}
                style={{ display: 'none' }}
                multiple
                accept=".tif,.tiff,.npy,.png,.jpg,.jpeg"
                onChange={(e) => e.target.files && handleAddFiles(e.target.files)}
              />
            </div>

            {selectedFiles.length > 0 && (
              <div className="selected-files-list">
                {selectedFiles.map((file, i) => (
                  <div className="selected-file-item" key={i}>
                    <span className="file-name">{file.name} ({(file.size / 1024).toFixed(0)}KB)</span>
                    <span className="remove-file-btn" onClick={(e) => { e.stopPropagation(); handleRemoveFile(i); }}>
                      ✕
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Query & Mode Panel */}
          <div className="panel query-panel">
            <div className="panel-header">
              <span className="panel-title">// QUERY INPUT</span>
              <span className="panel-badge">MODE: {currentMode.toUpperCase()}</span>
            </div>

            <div className="query-input-box">
              <textarea
                className="query-textarea"
                placeholder="e.g. What percentage of this area is covered by water?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              ></textarea>

              <div className="mode-selector-row">
                {['auto', 'single', 'cross_modal', 'temporal'].map((mode) => (
                  <button
                    key={mode}
                    className={`mode-btn ${currentMode === mode ? 'active' : ''}`}
                    onClick={() => setCurrentMode(mode)}
                  >
                    {mode.replace('_', '-').toUpperCase()}
                  </button>
                ))}
              </div>

              <div className="query-actions">
                <span className="keyboard-hint">SELECT MODE AND RUN ANALYSIS</span>
                <button
                  className={`run-query-btn ${isSubmitting ? 'disabled' : ''}`}
                  onClick={handleSubmitAnalysis}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'SUBMITTING...' : 'ANALYZE'}
                </button>
              </div>
            </div>
          </div>

          {/* Demo Scenarios & Recent Runs */}
          <div className="panel demo-runs-panel" id="guide">
            <div className="panel-header">
              <span className="panel-title">// DEMO SCENARIOS</span>
            </div>
            <div className="demo-grid">
              <button
                className="demo-btn"
                onClick={() => handleSetDemo('Describe the land cover in this scene', 'auto')}
              >
                Land Cover
              </button>
              <button
                className="demo-btn"
                onClick={() => handleSetDemo('Detect water bodies and estimate area', 'auto')}
              >
                Water Detection
              </button>
              <button
                className="demo-btn"
                onClick={() => handleSetDemo('Highlight urban/built-up regions', 'auto')}
              >
                Urban Areas
              </button>
              <button
                className="demo-btn"
                onClick={() => handleSetDemo('What has changed between these two dates?', 'temporal')}
              >
                Change Analysis
              </button>
              <button
                className="demo-btn"
                onClick={() => handleSetDemo('Compare SAR and optical modalities', 'cross_modal')}
              >
                Cross-Modal
              </button>
              <button
                className="demo-btn"
                onClick={() => handleSetDemo('Show vegetation health using NDVI', 'auto')}
              >
                NDVI Vegetation
              </button>
            </div>

            {recentRuns.length > 0 && (
              <div className="recent-runs-section" id="logs">
                <div className="section-subtitle">// RECENT RUNS</div>
                <div className="recent-runs-list">
                  {recentRuns.map((r) => (
                    <div className="recent-run-item" key={r.run_id} onClick={() => loadRun(r.run_id)}>
                      <span className="run-id-text">{r.run_id.slice(0, 16)} · {r.status}</span>
                      <span className="run-query-text">{(r.query || '').slice(0, 25)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Workflow Cockpit Monitor & Results Panel */}
          <div className="panel results-panel">
            <div className="panel-header">
              <span className="panel-title">// COCKPIT MONITOR & RESULTS</span>
              {runData && (
                <span className={`panel-badge ${runData.status === 'executing' ? 'active-pulse' : ''}`}>
                  {runData.status ? runData.status.toUpperCase() : 'IDLE'}
                </span>
              )}
            </div>

            {!runData ? (
              <div className="results-placeholder">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="M12 8v4M12 16h.01" />
                </svg>
                <p>Upload satellite images and execute query to view analysis workflow and results.</p>
              </div>
            ) : (
              <div className="dashboard-results-container">
                {/* Status Bar */}
                <div className="run-status-bar">
                  <span className={`status-badge ${runData.status || 'unknown'}`}>{runData.status}</span>
                  <div className="progress-bar-container">
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${runData.status === 'completed' ? 100 : (runData.progress || 0) * 100}%` }}
                    ></div>
                  </div>
                  <span className="run-id-label">{runData.run_id}</span>
                </div>

                {/* Answer Card */}
                {runData.answer ? (
                  <div className="answer-section">
                    <div className="section-subtitle">// ANSWER</div>
                    <div className="answer-card-content">{runData.answer}</div>

                    {runData.confidence != null && (
                      <div className="confidence-meter-row">
                        <span className="confidence-val">
                          {Math.round(runData.confidence * 100)}% CONFIDENCE
                        </span>
                        <div className="confidence-track">
                          <div
                            className="confidence-fill"
                            style={{
                              width: `${runData.confidence * 100}%`,
                              backgroundColor:
                                runData.confidence > 0.7
                                  ? 'var(--green)'
                                  : runData.confidence > 0.5
                                  ? 'var(--yellow)'
                                  : 'var(--red)'
                            }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : runData.current_step ? (
                  <div className="answer-card-content step-loading">
                    {runData.current_step}...
                  </div>
                ) : null}

                {/* Evidence List */}
                {runData.evidence && runData.evidence.length > 0 && (
                  <div className="evidence-section">
                    <div className="section-subtitle">// EVIDENCE ({runData.evidence.length})</div>
                    <div className="evidence-list">
                      {runData.evidence.map((item, idx) => (
                        <div key={idx} className="evidence-item-box">
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Visual Outputs */}
                {runData.visual_outputs && runData.visual_outputs.length > 0 && (
                  <div className="visuals-section">
                    <div className="section-subtitle">// VISUAL OUTPUTS</div>
                    <div className="visuals-grid">
                      {runData.visual_outputs.map((v, idx) => {
                        const imgUrl = resolveVisualUrl(runData.run_id, v.url);
                        return (
                          <div key={idx} className="visual-card">
                            <img
                              src={imgUrl}
                              alt={v.label || v.type}
                              onError={(e) => (e.currentTarget.style.display = 'none')}
                              loading="lazy"
                            />
                            <div className="visual-card-label">{v.label || v.type}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Execution Trace & Timeline */}
                {runData.trace && (runData.trace.tool_logs?.length > 0 || runData.trace.parallel_groups?.length > 0) && (
                  <div className="trace-section">
                    <div className="section-subtitle">// EXECUTION TRACE</div>
                    {runData.trace.parallel_groups?.length > 0 && (
                      <div className="trace-groups">
                        {runData.trace.parallel_groups.map((group, gIdx) => (
                          <div key={gIdx} className="trace-group-row">
                            <span className="trace-group-tag">G{gIdx + 1}</span>
                            {group.map((toolName, tIdx) => {
                              const log = (runData.trace.tool_logs || []).find((l) => l.tool === toolName) || {};
                              const status = log.status || 'running';
                              return (
                                <span key={tIdx} className={`tool-chip ${status}`}>
                                  {toolName}
                                  {log.runtime_ms ? <span className="ms">{log.runtime_ms}ms</span> : null}
                                </span>
                              );
                            })}
                          </div>
                        ))}
                      </div>
                    )}

                    {runData.trace.tool_logs?.length > 0 && (
                      <div className="timeline-container">
                        {(() => {
                          const maxMs = Math.max(
                            ...runData.trace.tool_logs.map((l) => l.runtime_ms || 0),
                            1
                          );
                          return runData.trace.tool_logs.map((log, lIdx) => {
                            const widthPct = Math.max(2, ((log.runtime_ms || 0) / maxMs) * 100);
                            const barColor =
                              log.status === 'success'
                                ? 'var(--green)'
                                : log.status === 'skipped'
                                ? 'var(--accent2)'
                                : 'var(--red)';
                            return (
                              <div key={lIdx} className="timeline-row">
                                <span className="timeline-name">{log.tool}</span>
                                <div className="timeline-bar-bg">
                                  <div
                                    className="timeline-bar"
                                    style={{ width: `${widthPct}%`, backgroundColor: barColor }}
                                  ></div>
                                </div>
                                <span className="timeline-ms">{log.runtime_ms || 0}ms</span>
                              </div>
                            );
                          });
                        })()}
                      </div>
                    )}
                  </div>
                )}

                {/* Report Buttons */}
                {runData.status === 'completed' && (
                  <div className="report-actions-row">
                    <a
                      className="report-btn"
                      href={apiPath(`/api/runs/${runData.run_id}/report?format=html`)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      HTML REPORT
                    </a>
                    <a
                      className="report-btn"
                      href={apiPath(`/api/runs/${runData.run_id}/report?format=json`)}
                      target="_blank"
                      rel="noreferrer"
                    >
                      JSON REPORT
                    </a>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Hero;
