"use client";

import * as THREE from "three";
import { useRef } from "react";
import { useFrame, ThreeElements, useLoader } from "@react-three/fiber";
import { TextureLoader } from "three";

export type DataBlockFallToBoxProps = ThreeElements["mesh"] & {
  texturePath: string;            // e.g. "/assets/yellow-datablock.png"
  boxY: number;                   // The Y coordinate of the user box (target), e.g. 1.45
  spawnXRange?: [number, number];  // Range for initial x position (before shifting)
  spawnYRange?: [number, number];  // Range for initial y position (spawn height)
  fallSpeed?: number;             // Falling speed (units per second)
  xOffset?: number;               // Additional offset added to the chosen x (to shift falling to the right)
};

export default function DataBlockFallToBox(props: DataBlockFallToBoxProps) {
  const {
    texturePath,
    boxY,
    spawnXRange = [-0.2, 0.2],
    spawnYRange = [6, 8],
    fallSpeed = 1.5,
    xOffset = 2.1,
  } = props;

  const meshRef = useRef<THREE.Mesh>(null!);

  // Define 5 fixed x positions within spawnXRange.
  const [minX, maxX] = spawnXRange;
  const fixedXPoints = [
    minX,
    minX + (maxX - minX) * 0.25,
    minX + (maxX - minX) * 0.5,
    minX + (maxX - minX) * 0.75,
    maxX,
  ];
  // Choose one fixed x and add the xOffset.
  const chooseFixedX = () => {
    const idx = Math.floor(Math.random() * fixedXPoints.length);
    return fixedXPoints[idx] + xOffset;
  };

  // Get a random initial Y from spawnYRange.
  const getRandomY = () => {
    const [minY, maxY] = spawnYRange;
    return Math.random() * (maxY - minY) + minY;
  };

  // On the first frame, initialize the block's position if not already done.
  if (meshRef.current && !meshRef.current.userData.initialized) {
    const initialX = chooseFixedX();
    const initialY = getRandomY();
    meshRef.current.position.set(initialX, initialY, -0.1);
    meshRef.current.userData.initialized = true;
  }

  const texture = useLoader(TextureLoader, texturePath);

  useFrame((_, delta) => {
    if (!meshRef.current) return;
    // Move the block down by updating its y coordinate.
    meshRef.current.position.y -= delta * fallSpeed;
    // When the block reaches or goes below the target (boxY), reset its position.
    if (meshRef.current.position.y <= boxY) {
      const newX = chooseFixedX();
      const newY = getRandomY();
      meshRef.current.position.set(newX, newY, -0.1);
    }
    // No rotation applied: the block falls "as is."
  });

  return (
    <mesh ref={meshRef}>
      <planeGeometry args={[0.15, 0.15]} />
      <meshStandardMaterial map={texture} transparent />
    </mesh>
  );
}
