'use client'

import * as THREE from 'three'
import React, { memo, useRef } from 'react'
import { useFrame, ThreeElements } from '@react-three/fiber'

const vmYPosition = -1.7;
const vmYPositionTop = vmYPosition + 0.5;

const colors = {
  utilization: '#FFFFFF',
  black: '#202124',
  red: '#EA4335',
  green: '#34A853',
  player1: '#FBBC04',
  player2: '#4285F4',
}

export default memo(function MessageIncoming(props: ThreeElements['mesh'] & { type: 'FAILURE', side: 'LEFT' | 'RIGHT' }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  useFrame((state, delta) => {
    meshRef.current.rotation.x += delta * 8
    meshRef.current.rotation.y += delta * 2
    if (meshRef.current.position.y > vmYPositionTop) {
      meshRef.current.position.y -= delta * 1
      if (props.side === 'LEFT') {
        meshRef.current.position.x -= delta * 2
      } else {
        meshRef.current.position.x += delta * 2
      }
    } else {
      meshRef.current.position.y -= delta * 4
    }
  });
  return (
    <mesh
      {...props}
      ref={meshRef}
    >
      <boxGeometry args={[0.1, 0.1, 0.1]} />
      <meshStandardMaterial color={colors.red} />
    </mesh>
  )
});
