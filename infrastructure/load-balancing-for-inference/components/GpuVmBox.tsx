"use client";

import React, { memo } from "react";
import { ThreeElements, useLoader } from "@react-three/fiber";
import { TextureLoader } from "three";
import Text from "@/components/Text";

const vmYPosition = -1.7;

export default memo(function GpuVmBox(
  props: ThreeElements["mesh"] & {
    utilization: number;
    vmXPosition: number;
    index: number;
    size?: [number, number]; // ✅ Added size prop (Width, Height)
  }
) {
  const { vmXPosition, utilization, index, size = [1.2, 1.2] } = props;
  const textSize = 0.4; // ✅ Adjusted text size for smaller boxes
  
  // Load GPU texture
  const gpuTexture = useLoader(TextureLoader, "/assets/GPU.png");

  // Determine color based on utilization
  const color = utilization >= 0.5 ? "#EA4335" : "#FBBC04"; // Red when high, Yellow when low

  return (
    <group key={vmXPosition}>
      {/* GPU Image */}
      <mesh position={[vmXPosition, vmYPosition, 0]}>
        <planeGeometry args={size} /> {/* ✅ Dynamic GPU box size */}
        <meshStandardMaterial map={gpuTexture} color={color} transparent />
      </mesh>
      
      {/* Utilization Indicator (Numbering) */}
      <Text
        displayText={(index + 1).toString()}
        position={[vmXPosition - textSize / 2, vmYPosition + 0.5, -0.2]}
        size={textSize}
      />
    </group>
  );
});
