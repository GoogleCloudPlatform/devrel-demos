"use client";

import React, { useState, useEffect, useRef } from "react";
import { useLoader } from "@react-three/fiber";
import { TextureLoader } from "three";
import Text from "@/components/Text";
import localFont from 'next/font/local';

// Load Jersey15 font
const jersey15 = localFont({
  src: '../public/fonts/Jersey15-Regular.ttf',
  variable: '--font-jersey15'
});

export type GpuStatus = {
  utilization: number;
};

export type GpuGroupProps = {
  positions: number[];  // Array of x positions for the GPUs (length should be 4)
  stats: GpuStatus[];   // Array of GPU status objects corresponding to these GPUs
};

const vmYPosition = -1.7; // Base Y position for GPUs
const gpuSize: [number, number] = [1.0, 1.9]; // GPU dimensions
const OVERFLOW_THRESHOLD = 0.95; // 95% utilization threshold for overflow
const BLOCK_SIZE = 0.15; // Size of overflow blocks (matching DataBlockFunnelToGPU)
const BLOCK_SPACING = 0.05; // Increased spacing between stacked blocks
const ANIMATION_INTERVAL = 150; // ms between adding/removing blocks

// Define specific X offsets for each GPU (index 0-3) - mirrored from left side
const GPU_BLOCK_OFFSETS = [-0.01, -0.04, -0.06, -0.08];

export default function GpuGroupRight({ positions, stats }: GpuGroupProps) {
  // Load the GPU texture once.
  const gpuTexture = useLoader(TextureLoader, "/assets/gpu-funnel-combine.png");
  
  // Load the blue datablock texture
  const dataBlockTexture = useLoader(TextureLoader, "/assets/blue-datablock.png");
  
  // State to track overflow blocks for each GPU
  const [overflowBlockCounts, setOverflowBlockCounts] = useState<number[]>([0, 0, 0, 0]);
  // Ref to store target block counts (for smooth animation)
  const targetBlockCountsRef = useRef<number[]>([0, 0, 0, 0]);
  
  // Calculate target block counts based on utilization
  useEffect(() => {
    stats.forEach((stat, index) => {
      const utilization = stat.utilization;
      
      if (utilization > OVERFLOW_THRESHOLD) {
        // Calculate target blocks based on overflow amount
        const targetBlocks = Math.min(5, Math.ceil((utilization - OVERFLOW_THRESHOLD) * 100));
        targetBlockCountsRef.current[index] = targetBlocks;
      } else {
        targetBlockCountsRef.current[index] = 0;
      }
    });
  }, [stats]);
  
  // Set up interval to animate block addition/removal
  useEffect(() => {
    const intervalId = setInterval(() => {
      let hasChanged = false;
      const newCounts = [...overflowBlockCounts];
      
      for (let i = 0; i < 4; i++) {
        const target = targetBlockCountsRef.current[i];
        const current = newCounts[i];
        
        if (target > current) {
          // Add one block
          newCounts[i] += 1;
          hasChanged = true;
        } else if (target < current) {
          // Remove one block
          newCounts[i] -= 1;
          hasChanged = true;
        }
      }
      
      if (hasChanged) {
        setOverflowBlockCounts([...newCounts]);
      }
    }, ANIMATION_INTERVAL);
    
    return () => clearInterval(intervalId);
  }, [overflowBlockCounts]);

  // Calculate position adjustment based on text length
  const getTextPositionX = (utilization: number): number => {
    const percentText = `${Math.round(utilization * 100)}%`;
    const length = percentText.length;
    
    // Base position
    const baseX = 0;
    
    // No adjustment needed for 4 characters (like "100%") as it's already centered
    if (length === 4) return baseX;
    
    // Apply small adjustments for shorter strings to center them properly
    if (length === 3) return baseX + 0.04; // for values like "99%"
    if (length === 2) return baseX + 0.08; // for values like "9%"
    
    return baseX; // default
  };

  return (
    <>
      {positions.map((xPos, index) => {
        const utilization = stats[index]?.utilization ?? 0;
        // Compute fill bar height and position.
        const fillHeight = utilization * 0.62;
        const fillPosition = vmYPosition - 0.76 + fillHeight / 2;
        // Color: For right side, if utilization < 0.5, use blue, else red
        const color = utilization >= 0.5 ? "#EA4335" : "#4285F4";

        // Generate overflow blocks
        const overflowBlocks = [];
        const blockCount = overflowBlockCounts[index];
        const gpuTopY = vmYPosition + ((gpuSize[1] / 2) - 0.91); // Top of GPU
        
        // Use custom offset for this specific GPU
        const xOffset = GPU_BLOCK_OFFSETS[index];
        
        for (let i = 0; i < blockCount; i++) {
          // Apply the custom offset for this GPU
          const blockPosition = [xPos + xOffset, gpuTopY + (i * (BLOCK_SIZE + BLOCK_SPACING)), 0.1];
          
          // Add the block with texture - using blue texture
          overflowBlocks.push(
            <mesh 
              key={`overflow-right-${index}-${i}`} 
              position={[blockPosition[0], blockPosition[1], 0.1]}
            >
              <planeGeometry args={[BLOCK_SIZE, BLOCK_SIZE]} />
              <meshStandardMaterial 
                map={dataBlockTexture}
                transparent 
                opacity={0.9} 
              />
            </mesh>
          );
        }

        // Calculate dynamic X position adjustment based on text length
        const textPositionX = getTextPositionX(utilization);

        return (
          <group key={`gpu-right-${index}`}>
            {/* GPU Image */}
            <mesh position={[xPos, vmYPosition, 0]}>
              <planeGeometry args={gpuSize} />
              <meshStandardMaterial map={gpuTexture} color={color} transparent />
            </mesh>
            
            {/* Fill Indicator */}
            <mesh position={[xPos, fillPosition, 0]}>
              <planeGeometry args={[0.63, fillHeight]} />
              <meshStandardMaterial color={color} />
            </mesh>

            {/* Utilization Percentage with dynamic positioning and enhanced font loading */}
            <Text
              displayText={`${Math.round(utilization * 100)}%`}
              position={[xPos - 0.17 + textPositionX, vmYPosition - 0.54, 0]}
              size={0.12}
              color="black"
              anchorX="center"
              anchorY="middle"
              font="/fonts/Jersey15-Regular.ttf"
              fontWeight="bold"
              className={jersey15.className}
              fontFace={{
                font: "Jersey15-Regular",
                weight: "bold"
              }}
            />
            
            {/* Overflow blocks */}
            {overflowBlocks}
          </group>
        );
      })}
    </>
  );
}