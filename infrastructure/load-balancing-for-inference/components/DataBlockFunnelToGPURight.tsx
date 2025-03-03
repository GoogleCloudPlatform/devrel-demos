"use client";
import * as THREE from "three";
import { useRef, useEffect } from "react";
import { useFrame, useLoader } from "@react-three/fiber";
import { TextureLoader } from "three";
export type DataBlockFunnelToGPURightProps = {
  texturePath: string; // e.g. "/assets/blue-datablock.png"
  funnelX: number;     // The funnel's current X coordinate
  funnelY: number;     // The funnel's Y coordinate
  gpuY: number;        // The GPU's Y coordinate (e.g. -1.7)
  onComplete: () => void;
  fallSpeed?: number;  // Falling speed (default: 4)
  gpuIndex?: number;   // Index of the GPU (0-3) to apply correct offset
  funnelNumber?: number; // The specific funnel number (1-4) to use different offsets
};

// Define specific X offsets for each funnel position (1-4) for right side
// Adjusted offsets to center blocks for all funnel positions
const FUNNEL_POSITION_OFFSETS = {
  1: -0.02,  // First funnel position (1.3) - working
  2: -0.2, // Second funnel position (2.5) - more negative
  3: -0.3,  // Third funnel position (3.7) - working
  4: -0.075  // Fourth funnel position (4.9) - more negative
};

export default function DataBlockFunnelToGPURight({
  texturePath,
  funnelX,
  funnelY,
  gpuY,
  onComplete,
  fallSpeed = 4,
  gpuIndex = 0,
  funnelNumber = 1
}: DataBlockFunnelToGPURightProps) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const groupRef = useRef<THREE.Group>(null!);
  
  // Constants for consistent sizing
  const BLOCK_SIZE = 0.15;
  
  // Get the appropriate X offset based on funnel position
  const xOffset = FUNNEL_POSITION_OFFSETS[funnelNumber] || 0;
  
  // Debug logging for position tuning (only on mount)
  useEffect(() => {
    console.log(`RIGHT Funnel ${funnelNumber} at X=${funnelX}, using offset=${xOffset}, final X=${funnelX + xOffset}`);
  }, []);
  
  // Load the data block texture.
  const texture = useLoader(TextureLoader, texturePath);
  
  // On mount, initialize the block's position with the correct offset
  useEffect(() => {
    if (groupRef.current) {
      // Apply the funnel-specific offset to the x position
      groupRef.current.position.set(funnelX + xOffset, funnelY + 0.3, 0.1);
    }
  }, [funnelX, funnelY, xOffset]);
  
  useFrame((_, delta) => {
    if (!groupRef.current) return;
    
    // Smoothly match the funnel's X (with appropriate offset)
    groupRef.current.position.x = THREE.MathUtils.lerp(
      groupRef.current.position.x,
      funnelX + xOffset,
      delta * 4
    );
    
    // Fall downward.
    groupRef.current.position.y -= delta * fallSpeed;
    
    // Once the block is below gpuY, call onComplete to remove it.
    if (groupRef.current.position.y <= gpuY) {
      onComplete();
    }
    
    // Keep rotation at 0 for a 2D effect.
    groupRef.current.rotation.set(0, 0, 0);
  });
  
  return (
    <group ref={groupRef}>
      {/* Actual datablock */}
      <mesh ref={meshRef} position={[0, 0, 0]}>
        <planeGeometry args={[BLOCK_SIZE, BLOCK_SIZE]} />
        <meshStandardMaterial 
          map={texture} 
          transparent 
          opacity={0.9} 
        />
      </mesh>
    </group>
  );
}