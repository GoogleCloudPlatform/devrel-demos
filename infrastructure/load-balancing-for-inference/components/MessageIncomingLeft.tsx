"use client";

import React, { useState, useEffect } from "react";
import DataBlockFallToBox from "./DataBlockFallToBox";
import DataBlockFunnelToGPU from "./DataBlockFunnelToGPU";

interface MessageIncomingLeftProps {
  showResults: boolean;
  funnelX: number; // from Player1 (current funnel x)
  player1VmXPositions: number[]; // from Player1 (all funnel x positions)
}

export default function MessageIncomingLeft({
  showResults,
  funnelX,
  player1VmXPositions
}: MessageIncomingLeftProps) {
  // Phase 1: Blocks falling from top to user box.
  const [phase1Blocks, setPhase1Blocks] = useState<string[]>([]);
  // Phase 2: Blocks falling from funnel to GPU.
  const [phase2Blocks, setPhase2Blocks] = useState<string[]>([]);

  // Freeze the initial funnelX for phase 1 blocks.
  const [frozenFunnelX] = useState(funnelX);

  // Coordinates.
  const userBoxY = 1.45; // target Y for phase 1
  const funnelY = 0.09;  // funnel Y for phase 2
  const gpuY = -1.7;     // GPU Y for phase 2

  // Maximum number of phase 2 blocks (increased from 4)
  const MAX_PHASE2_BLOCKS = 8;
  // Faster spawn interval (ms) for more blocks
  const SPAWN_INTERVAL = 400; // was 800ms

  // Determine which funnel position (1-4) is currently active
  const getCurrentFunnelIndex = () => {
    const index = player1VmXPositions.findIndex(pos => Math.abs(pos - funnelX) < 0.1);
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

  // Continuously spawn phase 2 blocks if active count is below MAX_PHASE2_BLOCKS.
  useEffect(() => {
    if (showResults) return;
    const interval = setInterval(() => {
      setPhase2Blocks((prev) =>
        prev.length < MAX_PHASE2_BLOCKS ? [...prev, crypto.randomUUID()] : prev
      );
    }, SPAWN_INTERVAL);
    return () => clearInterval(interval);
  }, [showResults]);

  // When a phase 2 block reaches the GPU, remove it.
  const handlePhase2Complete = (id: string) => {
    setPhase2Blocks((prev) => prev.filter((pid) => pid !== id));
  };

  if (showResults) return null;

  // Define funnel-specific offsets based on position
  const FUNNEL_X_OFFSETS = {
    1: 0.125,
    2: 0.125, 
    3: 0.125,
    4: -0.1
  };

  // Get current active funnel number
  const currentFunnelNumber = getCurrentFunnelNumber();
  
  // Function to get slightly randomized fall speeds for visual variety
  const getRandomFallSpeed = () => {
    return 2.5 + Math.random() * 1.5; // Between 2.5 and 4
  };

  return (
    <>
      {/* Phase 1: Blocks falling from top to user box */}
      {phase1Blocks.map((id) => (
        <DataBlockFallToBox
          key={id}
          texturePath="/assets/yellow-datablock.png"
          boxY={userBoxY}
          onComplete={() => handlePhase1Complete(id)}
          spawnXRange={[frozenFunnelX - 0.4, frozenFunnelX + 0.4]}
          spawnYRange={[4, 6]}
          fallSpeed={getRandomFallSpeed()} // Randomized fall speed for visual variety
          xOffset={1.0} // Restore rightward shift for phase 1
        />
      ))}

      {/* Phase 2: Blocks falling from funnel to GPU */}
      {phase2Blocks.map((id) => (
        <DataBlockFunnelToGPU
          key={id}
          texturePath="/assets/yellow-datablock.png"
          funnelX={funnelX}
          funnelY={funnelY}
          gpuY={gpuY}
          onComplete={() => handlePhase2Complete(id)}
          fallSpeed={getRandomFallSpeed()} // Randomized fall speed for visual variety
          gpuIndex={getCurrentFunnelIndex()}
          funnelNumber={currentFunnelNumber}
        />
      ))}
    </>
  );
}