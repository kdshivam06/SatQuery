import React, { useEffect, useRef } from 'react';
import Globe from 'globe.gl';
import { MeshLambertMaterial, DoubleSide } from 'three';
import * as topojson from 'topojson-client';
import landTopo from 'world-atlas/land-110m.json';

const HollowGlobe = () => {
  const globeContainerRef = useRef(null);
  const globeInstance = useRef(null);

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

    // Cleanup function on unmount
    return () => {
      if (globeContainerRef.current) {
        globeContainerRef.current.innerHTML = '';
      }
    };
  }, []); // Empty dependency array ensures this runs only once on mount

  return (
    <div 
      ref={globeContainerRef} 
      style={{ margin: 0, width: '100vw', height: '100vh' }} 
    />
  );
};

export default HollowGlobe;
