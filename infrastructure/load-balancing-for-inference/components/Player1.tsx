"use client";

import { useLoader } from "@react-three/fiber";
import { useEffect, useState, useRef } from "react";
import { TextureLoader, MeshBasicMaterial, NearestFilter } from "three";
import MessageIncomingLeft from "./MessageIncomingLeft";

const player1VmXPositions: number[] = [-4.9, -3.7, -2.5, -1.3]; // Explicitly typed
const userFunnelBaseY = 0.28;

export default function Player1({ showResults }: { showResults: boolean }) {
  const [funnelX, setFunnelX] = useState<number>(player1VmXPositions[0]);
  const materialRef = useRef<MeshBasicMaterial | null>(null);
  const funnelMaterialRef = useRef<MeshBasicMaterial | null>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const keyToIndex: { [key: string]: number } = {
        Digit1: 0,
        Digit2: 1,
        Digit3: 2,
        Digit4: 3,
      };
      if (event.code in keyToIndex) {
        setFunnelX(player1VmXPositions[keyToIndex[event.code]]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const userBoxTexture = useLoader(TextureLoader, "/assets/user-box.png");
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

  return (
    <>
      {/* User Box with enhanced color preservation */}
      <mesh position={[-3.1, 1.45, 0]}>
        <planeGeometry args={[4.8, 1.7]} />
        <meshBasicMaterial 
          ref={materialRef}
          map={userBoxTexture} 
          transparent 
          color="#FFFFFF"
          toneMapped={false}
        />
      </mesh>

      {/* Funnel with enhanced color preservation */}
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

      {/* Phase 1 & Phase 2 falling blocks */}
      <MessageIncomingLeft 
        showResults={showResults} 
        funnelX={funnelX} 
        player1VmXPositions={player1VmXPositions} 
      />
    </>
  );
} 