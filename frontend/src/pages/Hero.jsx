import React, { useState, useRef } from 'react';
import '../styles/hero.css';

const Hero = ({ isPreloaded = true }) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [queryInput, setQueryInput] = useState('');
  const [isWorkflowActive, setIsWorkflowActive] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [workflowLogs, setWorkflowLogs] = useState([
    { time: '00:00.12', text: 'System ready. Waiting for input query or GeoTIFF data.' },
  ]);
  const [generatedInfo, setGeneratedInfo] = useState(null);
  const fileInputRef = useRef(null);

  // Workflow steps pipeline
  const workflowSteps = [
    { label: 'GeoTIFF Georeference & CRS Validation', status: 'idle' },
    { label: 'Multi-Spectral Band Alignment (B4, B8, B11)', status: 'idle' },
    { label: 'Vegetation & Water Index Computation (NDVI/NDWI)', status: 'idle' },
    { label: 'Llama-B-17 AI Query Synthesis', status: 'idle' },
  ];

  // Handle Drag & Drop
  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const processFile = (file) => {
    if (!file) return;
    const isGeoTIFF = file.name.endsWith('.tif') || file.name.endsWith('.tiff') || file.name.endsWith('.geotiff');
    
    setSelectedFile({
      name: file.name,
      size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
      type: file.type || 'image/tiff',
      isValidGeoTIFF: isGeoTIFF,
      crs: 'EPSG:4326 (WGS 84)',
      bands: 'RGB + NIR + SWIR (04 Bands)',
    });

    addLog(`Loaded file: ${file.name} [${(file.size / (1024 * 1024)).toFixed(2)} MB]`);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const addLog = (msg) => {
    const timestamp = new Date().toISOString().substring(14, 22);
    setWorkflowLogs((prev) => [...prev.slice(-8), { time: timestamp, text: msg }]);
  };

  // Simulate Workflow Execution when user runs a query
  const handleRunQuery = () => {
    if (!queryInput.trim() && !selectedFile) return;

    setIsWorkflowActive(true);
    setActiveStep(1);
    addLog(`Initiating workflow query: "${queryInput || 'Default GeoTIFF Scan'}"`);

    setTimeout(() => {
      setActiveStep(2);
      addLog('Extracting multi-spectral bands & georeferenced coordinates...');
    }, 1000);

    setTimeout(() => {
      setActiveStep(3);
      addLog('Calculating NDVI index & land classification matrices...');
    }, 2000);

    setTimeout(() => {
      setActiveStep(4);
      addLog('Synthesizing spatial intelligence output with Llama-B-17...');
    }, 3000);

    setTimeout(() => {
      setActiveStep(5);
      setIsWorkflowActive(false);
      addLog('Query execution complete. Generated intelligence output updated below.');

      // Update Generated Information Panel
      setGeneratedInfo({
        queryExecuted: queryInput || 'Satellite Raster Multi-Spectral Analysis',
        filename: selectedFile ? selectedFile.name : 'SENTINEL2_AOI_KIRKLAND.tif',
        bbox: '12.9716° N, 77.5946° E (AOI-Delta-X)',
        meanNDVI: '0.742 (High Vegetation Density)',
        meanNDWI: '-0.128 (Low Moisture Depletion)',
        waterBodyArea: '14.2 km²',
        aiSummary:
          'Satellite imagery reveals dense canopy coverage with moderate surface water retention across the requested region. No thermal anomaly detected.',
      });
    }, 4000);
  };

  return (
    <div className={`hero ${!isPreloaded ? 'hero-revealed' : ''}`}>
      <div className="preloader-revealer"></div>

      {/* Top Header Navigation */}
      <header className="hero-header">
        <div className="hero-title">
          <div className="hero-title-line">
            <span className="hero-title-word">SATQUERY</span>
          </div>
        </div>

        <nav className="hero-nav">
          <a href="#workspace" className="nav-link">WORKSPACE</a>
          <a href="#logs" className="nav-link">LOGS</a>
          <a href="#guide" className="nav-link">GUIDE</a>
        </nav>
      </header>

      {/* 2-Column Split Viewport Main Container */}
      <div className="hero-viewport-grid">
        
        {/* LEFT COLUMN */}
        <div className="grid-column left-column">
          
          {/* Top: GeoTIFF Drag & Drop Zone */}
          <div className="panel dropzone-panel">
            <div className="panel-header">
              <span className="panel-badge">INPUT DATASET</span>
              <span className="panel-title">GeoTIFF Raster Upload</span>
            </div>

            <div
              className={`dropzone-box ${isDragging ? 'dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept=".tif,.tiff,.geotiff"
                style={{ display: 'none' }}
              />

              <div className="dropzone-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>

              <div className="dropzone-text">
                {selectedFile ? (
                  <div className="selected-file-info">
                    <span className="file-name">{selectedFile.name}</span>
                    <span className="file-meta">{selectedFile.size} • {selectedFile.crs}</span>
                    <span className="file-status">✓ Georeferencing Verified</span>
                  </div>
                ) : (
                  <>
                    <p className="drop-prompt">Drag & Drop GeoTIFF (.tif / .geotiff) file here</p>
                    <p className="drop-subtext">or click to browse your spatial raster files</p>
                  </>
                )}
              </div>

              <div className="geotiff-description">
                <p>
                  <strong>GeoTIFF Metadata Info:</strong> GeoTIFF files encapsulate georeferenced spatial rasters, coordinate reference systems (CRS), bounding coordinates, and multi-spectral satellite imagery bands used for Earth observation analytics.
                </p>
              </div>
            </div>
          </div>

          {/* Bottom: Generated Information Container */}
          <div className="panel results-panel">
            <div className="panel-header">
              <span className="panel-badge">OUTPUT INTELLIGENCE</span>
              <span className="panel-title">Generated Analysis Information</span>
            </div>

            <div className="results-content">
              {generatedInfo ? (
                <div className="results-grid">
                  <div className="result-card">
                    <span className="card-label">Target Query</span>
                    <span className="card-value highlight">{generatedInfo.queryExecuted}</span>
                  </div>

                  <div className="result-card">
                    <span className="card-label">Spatial Coordinates (BBox)</span>
                    <span className="card-value">{generatedInfo.bbox}</span>
                  </div>

                  <div className="result-card-row">
                    <div className="result-card">
                      <span className="card-label">Mean NDVI</span>
                      <span className="card-value metric">{generatedInfo.meanNDVI}</span>
                    </div>
                    <div className="result-card">
                      <span className="card-label">Surface Water Area</span>
                      <span className="card-value metric">{generatedInfo.waterBodyArea}</span>
                    </div>
                  </div>

                  <div className="result-card full-width">
                    <span className="card-label">Llama-B-17 Synthesis Report</span>
                    <p className="ai-report">{generatedInfo.aiSummary}</p>
                  </div>
                </div>
              ) : (
                <div className="results-placeholder">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                    <rect x="3" y="3" width="18" height="18" rx="2" strokeDasharray="3 3"/>
                    <path d="M3 9h18M9 21V9"/>
                  </svg>
                  <p>Generated analytics and spatial indices will appear here after executing a query.</p>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* RIGHT COLUMN */}
        <div className="grid-column right-column">
          
          {/* Top: Background Workflow Monitor Container */}
          <div className="panel monitor-panel">
            <div className="panel-header">
              <span className={`panel-badge ${isWorkflowActive ? 'active-pulse' : ''}`}>
                {isWorkflowActive ? 'WORKFLOW IN PROGRESS' : 'BACKGROUND MONITOR'}
              </span>
              <span className="panel-title">Pipeline Orchestrator</span>
            </div>

            <div className="workflow-pipeline">
              {workflowSteps.map((step, idx) => {
                const stepNum = idx + 1;
                const isDone = activeStep > stepNum;
                const isCurrent = activeStep === stepNum && isWorkflowActive;

                return (
                  <div key={idx} className={`pipeline-step ${isDone ? 'done' : ''} ${isCurrent ? 'current' : ''}`}>
                    <div className="step-indicator">
                      {isDone ? '✓' : isCurrent ? '⚡' : stepNum}
                    </div>
                    <span className="step-label">{step.label}</span>
                    <span className="step-status">
                      {isDone ? 'COMPLETE' : isCurrent ? 'RUNNING' : 'WAITING'}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Workflow Event Log Stream */}
            <div className="log-stream">
              <div className="log-stream-header">SYSTEM EVENTS LOG</div>
              <div className="log-entries">
                {workflowLogs.map((log, i) => (
                  <div key={i} className="log-line">
                    <span className="log-time">[{log.time}]</span>
                    <span className="log-text">{log.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Bottom: Query Text Input Section */}
          <div className="panel query-panel">
            <div className="panel-header">
              <span className="panel-badge">QUERY CONSOLE</span>
              <span className="panel-title">Natural Language Spatial Query</span>
            </div>

            <div className="query-input-box">
              <textarea
                className="query-textarea"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="Type your satellite query (e.g. Calculate vegetation health index, detect water bodies, or classify land cover)..."
                rows={3}
              />

              <div className="query-actions">
                <span className="keyboard-hint">Press Enter to execute</span>
                <button
                  className={`run-query-btn ${isWorkflowActive ? 'disabled' : ''}`}
                  onClick={handleRunQuery}
                  disabled={isWorkflowActive}
                >
                  {isWorkflowActive ? 'Processing Pipeline...' : 'Run Query ⚡'}
                </button>
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
};

export default Hero;