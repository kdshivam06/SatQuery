import React, { useEffect, useRef } from 'react';
import Globe from 'globe.gl';
import { MeshLambertMaterial, DoubleSide } from 'three';
import * as topojson from 'topojson-client';
import landTopo from 'world-atlas/land-110m.json';

const HollowGlobe = () => {
  const globeContainerRef = useRef(null);
  const globeInstance = useRef(null);
  const animFrameRef = useRef(null);

  useEffect(() => {
    // Ensure the container exists and the globe hasn't been initialized yet
    if (!globeContainerRef.current) return;

    // Initialize the Globe
    globeInstance.current = Globe()(globeContainerRef.current)
      .backgroundColor('rgba(0,0,0,0)')
      .showGlobe(false)
      .showAtmosphere(false);

    const land = topojson.feature(landTopo, landTopo.objects.land);
    globeInstance.current
      .polygonsData(land.features)
      .polygonCapMaterial(
        new MeshLambertMaterial({ color: 'darkslategrey', side: DoubleSide })
      )
      .polygonSideColor(() => 'rgba(0,0,0,0)');

    // Disable user orbit controls so rotation is purely programmatic
    globeInstance.current.controls().enabled = false;

    // Auto-rotate: increment longitude each frame (~0.15°/frame = ~9°/sec at 60fps)
    let lng = 0;
    const rotate = () => {
      lng = (lng + 0.15) % 360;
      globeInstance.current.pointOfView({ lat: 20, lng, altitude: 2 });
      animFrameRef.current = requestAnimationFrame(rotate);
    };
    animFrameRef.current = requestAnimationFrame(rotate);

    // Cleanup on unmount
    return () => {
      cancelAnimationFrame(animFrameRef.current);
      if (globeContainerRef.current) {
        globeContainerRef.current.innerHTML = '';
      }
    };
  }, []);

  return (
    <div
      ref={globeContainerRef}
      style={{ margin: 0, width: '100vw', height: '100vh' }}
    />
  );
};

export default HollowGlobe;
