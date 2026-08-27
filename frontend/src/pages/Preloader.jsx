import React, { useRef, useState, useEffect } from 'react';
import gsap from 'gsap';
import { runIntroAnimation, runExitAnimation } from '../animations/preloaderAnimation';
import Hero from './Hero';

const Preloader = () => {
  const containerRef = useRef(null);
  const [isReady, setIsReady] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  // Check if preloader should run (runs on hard refresh or initial tab load, skipped on soft route navigations)
  const shouldRunPreloader = () => {
    try {
      const navEntries = performance.getEntriesByType('navigation');
      const isReload = navEntries.length > 0 && navEntries[0].type === 'reload';

      if (isReload) {
        // Hard refresh: always play preloader sequence
        sessionStorage.removeItem('hasCompletedPreloader');
        return true;
      }

      // Skip if already completed during soft navigation
      const hasRun = sessionStorage.getItem('hasCompletedPreloader') === 'true';
      return !hasRun;
    } catch (e) {
      return true;
    }
  };

  const [showPreloader] = useState(shouldRunPreloader);

  useEffect(() => {
    if (!showPreloader) return;

    const ctx = gsap.context(() => {
      runIntroAnimation(containerRef.current, () => {
        setIsReady(true);
      });
    }, containerRef);

    return () => ctx.revert();
  }, [showPreloader]);

  const handleInitiateClick = () => {
    if (!isReady || isExiting) return;
    setIsExiting(true);
    runExitAnimation(containerRef.current, () => {
      sessionStorage.setItem('hasCompletedPreloader', 'true');
    });
  };

  // If preloader was already run in this session and not hard refreshed, directly render Hero
  if (!showPreloader) {
    return <Hero isPreloaded={false} />;
  }

  return (
    <div ref={containerRef}>
      {/* Backdrop initialization elements */}
      <div className="preloader-backdrop">
        <div className="pb-row">
          <div className="pb-col"><p>Initializing ...</p></div>
          <div className="pb-col"><p>// ///// // /// //</p></div>
          <div className="pb-col"><p>threshold &gt; 87%...</p></div>
          <div className="pb-col"><p>::;../&amp;::</p></div>
          <div className="pb-col"><p>return --parameters---</p></div>
        </div>

        <div className="pb-row">
          <div className="pb-col"><p>model-IP64 0xA7</p><p>Orchestrating...</p></div>
          <div className="pb-col"><p>field module / delta-x</p></div>
          <div className="pb-col">Spectral domain expansion ---75AT6</div>
          <div className="pb-col"><p>SAR-optical co-registration</p><p>Phase sync - 98%</p></div>
          <div className="pb-col"><p>Entropy +/- 0.03</p></div>
          <div className="pb-col"><p>AI model Llama-B-17</p></div>
        </div>
      </div>

      {/* Main Preloader Overlay */}
      <div className="preloader">
        <div className="p-row">
          <p>
            <span className="line-wrapper">
              <span className="line">Initiating</span>
            </span>
          </p>
        </div>

        <div className="p-row">
          <div className="p-col">
            <div className="p-sub-col">
              <p>
                <span className="line-wrapper">
                  <span className="line">Version 1.0</span>
                </span>
              </p>
              <p>
                <span className="line-wrapper">
                  <span className="line">Loading Domain Expansion</span>
                </span>
              </p>
            </div>
            <div className="p-sub-col">
              <p>
                <span className="line-wrapper">
                  <span className="line">Scanning...</span>
                </span>
              </p>
              <p>
                <span className="line-wrapper">
                  <span className="line">07 Layers</span>
                </span>
              </p>
            </div>
          </div>
          <div className="p-col">
            <p>
              <span className="line-wrapper">
                <span className="line">SQ-BETA-v1.0</span>
              </span>
            </p>
          </div>
        </div>

        {/* Initiate Button Container */}
        <div 
          className="preloader-btn-container" 
          onClick={handleInitiateClick}
          role="button"
          tabIndex={0}
          style={{ cursor: isReady && !isExiting ? 'pointer' : 'default' }}
        >
          <div id="pbc-logo">
            <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="16" stroke="#ffffff" strokeWidth="1.5" strokeDasharray="3 3"/>
              <circle cx="20" cy="20" r="6" fill="#ffffff"/>
              <path d="M20 0V8M20 32V40M0 20H8M32 20H40" stroke="#ffffff" strokeWidth="1.5"/>
            </svg>
          </div>
          
          <p id="pbc-label">
            <span className="line-wrapper">
              <span className="line">Initiate</span>
            </span>
          </p>
          
          <p id="pbc-outro-label">
            <span className="line-wrapper">
              <span className="line">Access Granted</span>
            </span>
          </p>

          <div className="pbc-svg-strokes">
            <svg
              width="320"
              height="320"
              viewBox="0 0 320 320"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle
                className="stroke-track"
                cx="160"
                cy="160"
                r="155"
                stroke="#2b2b2b"
                strokeWidth="2"
                strokeDasharray="974"
                strokeDashoffset="974"
              />

              <circle
                className="stroke-progress"
                cx="160"
                cy="160"
                r="155"
                stroke="#ffffff"
                strokeWidth="2"
                strokeDasharray="974"
                strokeDashoffset="974"
              />
            </svg>
          </div>
        </div>
      </div>

      {/* Hero Section Revealed after Preloader */}
      <Hero isPreloaded={true} />
    </div>
  );
};

export default Preloader;