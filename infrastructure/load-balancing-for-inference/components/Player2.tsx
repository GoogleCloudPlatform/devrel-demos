"use client";

import React, { useState, useEffect, useRef } from "react";
import { useLoader } from "@react-three/fiber";
import { TextureLoader, MeshBasicMaterial, NearestFilter } from "three";
import MessageIncomingRight from "./MessageIncomingRight";
import GpuGroupRight from "./GpuGroupRight";

const userFunnelBaseY = 0.28;
const player2VmXPositions = [1.3, 2.5, 3.7, 4.9]; // Mirror of Player1 positions

interface Player2Props {
  showResults: boolean;
  funnelX: number; // Accept funnelX from props
}

export default function Player2({ showResults, funnelX }: Player2Props) {
  const materialRef = useRef<MeshBasicMaterial | null>(null);
  const funnelMaterialRef = useRef<MeshBasicMaterial | null>(null);
  
  const userBoxTexture = useLoader(TextureLoader, "/assets/bot-box-3.png");
  const userFunnelTexture = useLoader(TextureLoader, "/assets/user-funnel.png");
  
  // Apply texture settings
  useEffect(() => {
    if (userBoxTexture) {
      userBoxTexture.magFilter = NearestFilter;
      userBoxTexture.minFilter = NearestFilter;
      userBoxTexture.needsUpdate = true;
    }
    
    if (userFunnelTexture) {
      userFunnelTexture.magFilter = NearestFilter;
      userFunnelTexture.minFilter = NearestFilter;
      userFunnelTexture.needsUpdate = true;
    }
    
    // Ensure material properties are set correctly
    if (materialRef.current) {
      materialRef.current.transparent = true;
      materialRef.current.map = userBoxTexture;
      materialRef.current.needsUpdate = true;
    }
    
    if (funnelMaterialRef.current) {
      funnelMaterialRef.current.transparent = true;
      funnelMaterialRef.current.map = userFunnelTexture;
      funnelMaterialRef.current.needsUpdate = true;
    }
  }, [userBoxTexture, userFunnelTexture]);
  
  // GPU stats with utilization data (mock data initially)
  const [gpuStats, setGpuStats] = useState([
    { utilization: 0 },
    { utilization: 0 },
    { utilization: 0 },
    { utilization: 0 }
  ]);
  
  // Mock function to update GPU utilization (for demonstration)
  useEffect(() => {
    // This is just a simple mock to show the concept
    const updateInterval = setInterval(() => {
      setGpuStats(current => {
        // Find the active GPU based on current funnel position
        const activeIndex = player2VmXPositions.findIndex(pos => Math.abs(pos - funnelX) < 0.1);
        if (activeIndex >= 0) {
          // Increase utilization for the active GPU
          const newStats = [...current];
          newStats[activeIndex] = {
            utilization: Math.min(1, newStats[activeIndex].utilization + 0.01)
          };
          
          // Slowly decrease other GPUs
          for (let i = 0; i < newStats.length; i++) {
            if (i !== activeIndex && newStats[i].utilization > 0) {
              newStats[i] = {
                utilization: Math.max(0, newStats[i].utilization - 0.005)
              };
            }
          }
          return newStats;
        }
        return current;
      });
    }, 200);
    
    return () => clearInterval(updateInterval);
  }, [funnelX]);

  return (
    <>
      {/* The user box for Player2 (top-right) with enhanced color rendering */}
      <mesh position={[2.9, 1.45, 0]}>
        <planeGeometry args={[4.8, 1.7]} />
        <meshBasicMaterial 
          ref={materialRef}
          map={userBoxTexture} 
          transparent 
          color="#FFFFFF"
          toneMapped={false}
        />
      </mesh>

      {/* The funnel for Player2 with enhanced color rendering */}
      <mesh position={[funnelX, userFunnelBaseY, 0]}>
        <planeGeometry args={[0.5, 0.7]} />
        <meshBasicMaterial 
          ref={funnelMaterialRef}
          map={userFunnelTexture} 
          transparent 
          color="#FFFFFF"
          toneMapped={false}
        />
      </mesh>
      
      {/* Falling blocks for Player2 */}
      <MessageIncomingRight 
        showResults={showResults} 
        funnelX={funnelX} 
      />
    </>
  );
}