'use client'

import * as THREE from 'three'
import React, { memo, useRef } from 'react'
import { useFrame, ThreeElements } from '@react-three/fiber'
import Text from "@/components/Text";

const vmYPosition = -1.7;

function getRGBColor(utilization: number) {
  // Calculate color components
  const red = 100 - (100 - 92) * utilization;
  const green = 100 - (100 - 26) * utilization;
  const blue = 100 - (100 - 21) * utilization;

  // Return the formatted RGB string
  return `rgb(${Math.round(red)}%, ${Math.round(green)}%, ${Math.round(blue)}%)`;
}

export default memo(function UtilizationBox(props: ThreeElements['mesh'] & { position: [number, number, number], utilization: number }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const { utilization } = props;
  const desiredYGeometry = utilization + 0.05;
  useFrame((state, delta) => {
    const yScale = meshRef.current.scale.y
    // increase and decrease utilization without bouncing up and down
    if (yScale + delta < desiredYGeometry) {
      meshRef.current.scale.y += delta / 4
    } else if (yScale - delta > desiredYGeometry) {
      meshRef.current.scale.y -= delta / 4
    }

    meshRef.current.position.y = vmYPosition - 0.5 + 0.5 * meshRef.current.scale.y;
  });

  const utilizationPercentage = Math.floor(props.utilization * 100);
  let ones = Math.floor(utilizationPercentage % 10);
  let tens = Math.floor(utilizationPercentage / 10 % 10) || ' ';
  let hundreds = Math.floor(utilizationPercentage / 100 % 10) || ' ';
  if (utilizationPercentage === 100) {
    ones = 0;
    tens = 0;
    hundreds = 1;
  }
  return (
    <group>
      <mesh
        {...props}
        ref={meshRef}
      >
        <boxGeometry args={[0.8, 1.0, 0.75]} />
        <meshStandardMaterial color={getRGBColor(utilization)} />
      </mesh>
      <Text
        position={[props.position[0] - 0.3, props.position[1], props.position[2] + 0.5]}
        displayText={`${hundreds}${tens}${ones}%`}
        size={0.2}
      />
    </group>
  )
});