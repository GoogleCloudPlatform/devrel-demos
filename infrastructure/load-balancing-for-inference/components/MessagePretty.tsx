"use client"

import type * as THREE from "three"
import { memo, useRef } from "react"
import { useFrame, type ThreeElements } from "@react-three/fiber"

const vmYPosition = -1.7
const vmYPositionTop = vmYPosition + 0.5
const playerEndYPosition = vmYPosition - 0.6
const loadBalancerXPosition = -6.0
const loadBalancerYPosition = vmYPositionTop + 2
const playerMidYPosition = loadBalancerYPosition

const startingBoxZ = -3

export default memo(function MessagePretty(
  props: ThreeElements["mesh"] & { endPoint: [number, number, number]; color: string },
) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const endPoint = props.endPoint

  useFrame((state, delta) => {
    meshRef.current.rotation.x += delta * 2
    meshRef.current.rotation.y += delta / 2
    const endingPointX = endPoint[0]

    // Update position based on current state
    if (meshRef.current.position.z > 0) {
      if (meshRef.current.position.y < playerMidYPosition - 0.5) {
        // Reset position when reaching bottom
        meshRef.current.position.y = 10 + 3 * Math.random()
        const isPlayer1 = endingPointX < 0
        meshRef.current.position.x = isPlayer1
          ? loadBalancerXPosition + Math.random() - 0.6
          : -loadBalancerXPosition - Math.random() + 0.6
        meshRef.current.position.z = startingBoxZ
      } else {
        meshRef.current.position.y -= delta * 4
      }
    } else if (meshRef.current.position.y < playerMidYPosition) {
      meshRef.current.position.y -= delta * 4
      meshRef.current.position.z = 0.01
    } else if (meshRef.current.position.y < playerMidYPosition + 0.1) {
      meshRef.current.position.x = endingPointX
      meshRef.current.position.y -= delta
    } else if (meshRef.current.position.y < playerMidYPosition + 0.2) {
      meshRef.current.position.x = endingPointX * 0.3 + meshRef.current.position.x * 0.7
      meshRef.current.position.y -= delta
    } else if (meshRef.current.position.y < playerMidYPosition + 0.5) {
      meshRef.current.position.x = endingPointX * 0.1 + meshRef.current.position.x * 0.9
      meshRef.current.position.y -= delta
    } else if (meshRef.current.position.z < 0 && meshRef.current.position.y < 3) {
      meshRef.current.position.y -= delta * 2
      const newZ = meshRef.current.position.z + delta * 5
      meshRef.current.position.z = newZ > 0 ? 0 : newZ
    } else if (meshRef.current.position.z < 0 && meshRef.current.position.y < 5) {
      meshRef.current.position.y -= delta * 2
      const newZ = meshRef.current.position.z + delta * 2
      meshRef.current.position.z = newZ > 0 ? 0 : newZ
    } else if (meshRef.current.position.z < 0 && meshRef.current.position.y < 10) {
      meshRef.current.position.y -= delta * 2
      const newZ = meshRef.current.position.z + delta / 2
      meshRef.current.position.z = newZ > 0 ? 0 : newZ
    } else {
      meshRef.current.position.y -= delta * 4
    }
  })

  return (
    <mesh {...props} ref={meshRef}>
      <boxGeometry args={[0.3, 0.15, 0.1]} /> {/* Increased size of boxes */}
      <meshStandardMaterial color={props.color} roughness={0.3} metalness={0.7} />
    </mesh>
  )
})

