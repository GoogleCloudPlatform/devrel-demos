"use client"

import * as THREE from "three"
import { memo, useRef, useMemo } from "react"
import { useFrame, type ThreeElements } from "@react-three/fiber"

const vmYPosition = -1.7
const vmYPositionTop = vmYPosition + 0.5
const playerEndYPosition = vmYPosition - 0.6
const loadBalancerXPosition = -2.9
const loadBalancerYPosition = vmYPositionTop + 2
const playerMidYPosition = loadBalancerYPosition

const startingBoxZ = -7

export default memo(function MessageIncoming(
  props: ThreeElements["mesh"] & {
    endPoint: [number, number, number]
    onVmContact: Function
    gameOver: boolean
    color: string
  },
) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const endPoint = props.endPoint

  // Create a custom geometry for a more interesting shape
  const geometry = useMemo(() => {
    const shape = new THREE.Shape()
    shape.moveTo(0, 0)
    shape.lineTo(0.05, 0.1)
    shape.lineTo(0.1, 0)
    shape.lineTo(0.05, -0.1)
    shape.lineTo(0, 0)

    const extrudeSettings = {
      steps: 1,
      depth: 0.05,
      bevelEnabled: true,
      bevelThickness: 0.01,
      bevelSize: 0.01,
      bevelSegments: 2,
    }

    return new THREE.ExtrudeGeometry(shape, extrudeSettings)
  }, [])

  useFrame((state, delta) => {
    if (!props.gameOver) {
      meshRef.current.rotation.x += delta * 2
      meshRef.current.rotation.y += delta / 2
      meshRef.current.rotation.z += delta * 1.5 // Add rotation around z-axis for more dynamic movement
    }
    const endingPointX = endPoint[0]
    if (meshRef.current.position.z > 0) {
      if (meshRef.current.position.y < playerEndYPosition) {
        // Has reached the bottom of the VM, ready to be reset
        if (!props.gameOver) {
          meshRef.current.position.y = 10 + 3 * Math.random()
          const isPlayer1 = endingPointX < 0
          meshRef.current.position.x = isPlayer1
            ? loadBalancerXPosition + Math.random() - 0.6
            : -loadBalancerXPosition - Math.random() + 0.6
          meshRef.current.position.z = startingBoxZ
          meshRef.current.scale.set(1, 1, 1) // Reset scale
        } else {
          // if game is over, incoming message should stay hidden under the VM
          meshRef.current.scale.set(0.0001, 0.0001, 0.0001)
        }
      } else {
        meshRef.current.position.y -= delta * 4
      }
    } else if (meshRef.current.position.y < playerMidYPosition) {
      meshRef.current.position.y -= delta * 4
      meshRef.current.position.z = 0.01
      props.onVmContact()
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
    <mesh {...props} ref={meshRef} geometry={geometry}>
      <meshPhongMaterial color={props.color} shininess={100} specular={new THREE.Color(0xffffff)} />
    </mesh>
  )
})

