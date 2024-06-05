'use client'

import React, { memo } from 'react'
import { ThreeElements } from '@react-three/fiber'
import Text from "@/components/Text";

const vmYPosition = -1.7;

const colors = {
  utilization: '#FFFFFF',
  black: '#202124',
  red: '#EA4335',
  green: '#34A853',
  player1: '#FBBC04',
  player2: '#4285F4',
}

export default memo(function EmptyVmBox(props: ThreeElements['mesh'] & { atMaxCapacity: boolean, vmXPosition: number, playerColor: string, index: number }) {
  const { vmXPosition, atMaxCapacity, playerColor } = props;
  const textSize = 0.5;
  return (
    <group key={vmXPosition} >
      <mesh position={[vmXPosition - 0.45, vmYPosition, 0]}>
        <boxGeometry args={[0.1, 1.0, 1.0]} />
        <meshStandardMaterial color={atMaxCapacity ? colors.red : playerColor} />
      </mesh>
      <mesh position={[vmXPosition + 0.45, vmYPosition, 0]}>
        <boxGeometry args={[0.1, 1.0, 1.0]} />
        <meshStandardMaterial color={atMaxCapacity ? colors.red : playerColor} />
      </mesh>
      <mesh position={[vmXPosition, vmYPosition, 0 - 0.45]}>
        <boxGeometry args={[1.0, 1.0, 0.1]} />
        <meshStandardMaterial color={atMaxCapacity ? colors.red : playerColor} />
      </mesh>
      <Text
        displayText={(props.index + 1)}
        position={[vmXPosition - textSize / 2, vmYPosition + 0.6, -0.2]}
        size={textSize}
      />
    </group>
  );
});
