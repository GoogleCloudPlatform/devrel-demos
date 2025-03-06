"use client";

import React, { useState, useEffect } from "react";
import DataBlockFallToBox from "./DataBlockFallToBox";
import DataBlockFunnelToGPURight from "./DataBlockFunnelToGPURight";

interface MessageIncomingRightProps {
  showResults: boolean;
  funnelX: number; // From Player2 (the current funnel x)
}

export default function MessageIncomingRight({
  showResults,
  funnelX,
}: MessageIncomingRightProps) {
  // Phase 1: Blocks falling from top to user box.
  const [phase1Blocks, setPhase1Blocks] = useState<string[]>([]);
  // Phase 2: Blocks falling from funnel to GPU.
  const [phase2Blocks, setPhase2Blocks] = useState<string[]>([]);

  // Freeze initial funnelX for phase 1 so blocks don't shift mid-fall.
  const [frozenFunnelX] = useState(funnelX);

  // Coordinates for right side:
  const userBoxY = 1.45; // target for phase 1
  const funnelY = 0.22;  // funnel Y position (matches Player1)
  const gpuY = -1.7;     // GPU Y position
  
  // All funnel positions for determining current index
  const player2VmXPositions = [1.3, 2.5, 3.7, 4.9]; // Mirror of Player1 positions

  // Determine which funnel position (1-4) is currently active
  const getCurrentFunnelIndex = () => {
    const index = player2VmXPositions.findIndex(pos => Math.abs(pos - funnelX) < 0.1);
    return index >= 0 ? index : 0; // Default to 0 if not found
  };

  // Get current funnel number (1-4) for display
  const getCurrentFunnelNumber = () => {
    return getCurrentFunnelIndex() + 1;
  };

  // On mount, spawn 10 phase 1 blocks.
  useEffect(() => {
    const ids = Array.from({ length: 10 }, () => crypto.randomUUID());
    setPhase1Blocks(ids);
  }, []);

  // When a phase 1 block reaches the user box, transition it to phase 2.
  const handlePhase1Complete = (id: string) => {
    setPhase1Blocks((prev) => prev.filter((pid) => pid !== id));
    setPhase2Blocks((prev) => [...prev, id]);
  };

  // Continuously spawn new phase 2 blocks if fewer than 8 are active (increased from 7)
  useEffect(() => {
    if (showResults) return;
    const interval = setInterval(() => {
      setPhase2Blocks((prev) =>
        prev.length < 8 ? [...prev, crypto.randomUUID()] : prev
      );
    }, 550); // Faster spawn rate (was 800ms)
    return () => clearInterval(interval);
  }, [showResults]);

  // Remove a phase 2 block when it reaches the GPU.
  const handlePhase2Complete = (id: string) => {
    setPhase2Blocks((prev) => prev.filter((pid) => pid !== id));
  };

  if (showResults) return null;

  // Calculate different fall speeds for more natural movement
  const getRandomFallSpeed = () => {
    return 2.5 + Math.random() * 1.5; // Between 2.5 and 4
  };

  return (
    <>
      {/* Phase 1: Blocks falling from top to user box */}
      {phase1Blocks.map((id) => (
        <DataBlockFallToBox
          key={id}
          texturePath="/assets/blue-datablock.png" // Right side color asset
          boxY={userBoxY}
          onComplete={() => handlePhase1Complete(id)}
          spawnXRange={[frozenFunnelX - 0.4, frozenFunnelX + 0.4]}
          spawnYRange={[4, 6]}
          fallSpeed={getRandomFallSpeed()} // More varied fall speeds
          xOffset={2.6}
        />
      ))}

      {/* Phase 2: Blocks falling from funnel to GPU */}
      {phase2Blocks.map((id) => (
        <DataBlockFunnelToGPURight
          key={id}
          texturePath="/assets/blue-datablock.png"
          funnelX={funnelX}
          funnelY={funnelY}
          gpuY={gpuY}
          onComplete={() => handlePhase2Complete(id)}
          fallSpeed={getRandomFallSpeed()} // More varied fall speeds
          gpuIndex={getCurrentFunnelIndex()}
          funnelNumber={getCurrentFunnelNumber()}
        />
      ))}
    </>
  );
}