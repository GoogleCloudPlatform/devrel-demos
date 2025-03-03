"use client";
import * as THREE from "three";
import { useRef, useEffect } from "react";
import { useFrame, useLoader } from "@react-three/fiber";
import { TextureLoader } from "three";
export type DataBlockFunnelToGPUProps = {
  texturePath: string; // e.g. "/assets/yellow-datablock.png"
  funnelX: number;     // The funnel's current X coordinate
  funnelY: number;     // The funnel's Y coordinate (e.g. 0.09)
  gpuY: number;        // The GPU's Y coordinate (e.g. -1.7)
  onComplete: () => void;
  fallSpeed?: number;  // Falling speed (default: 4)
  gpuIndex?: number;   // Index of the GPU (0-3) to apply correct offset
  funnelNumber?: number; // The specific funnel number (1-4) to use different offsets
};

// Define specific X offsets for each funnel position (1-4)
// These need to be calibrated based on your specific funnel positions
const FUNNEL_POSITION_OFFSETS = {
  1: 0.10,  // First funnel position (-4.9)
  2: 0.085,   // Second funnel position (-3.7)
  3: 0.05,   // Third funnel position (-2.5)
  4: 0.035    // Fourth funnel position (-1.3)
};

export default function DataBlockFunnelToGPU({
  texturePath,
  funnelX,
  funnelY,
  gpuY,
  onComplete,
  fallSpeed = 4,
  gpuIndex = 0,
  funnelNumber = 1
}: DataBlockFunnelToGPUProps) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const groupRef = useRef<THREE.Group>(null!);
  
  // Constants for consistent sizing
  const BLOCK_SIZE = 0.15;
  
  // Get the appropriate X offset based on funnel position
  const xOffset = FUNNEL_POSITION_OFFSETS[funnelNumber] || 0;
  
  // For debugging - log the position data
  useEffect(() => {
    console.log(`Funnel ${funnelNumber} at X=${funnelX}, using offset=${xOffset}, final X=${funnelX + xOffset}`);
  }, [funnelX, xOffset, funnelNumber]);
  
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