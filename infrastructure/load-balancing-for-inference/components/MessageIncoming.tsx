'use client'

import * as THREE from 'three'
import React, { memo, useRef } from 'react'
import { useFrame, ThreeElements } from '@react-three/fiber'

const vmYPosition = -1.7;
const vmYPositionTop = vmYPosition + 0.5;
const playerEndYPosition = vmYPosition - 0.6;
const loadBalancerXPosition = -2.9;
const loadBalancerYPosition = vmYPositionTop + 2;
const playerMidYPosition = loadBalancerYPosition;

const startingBoxZ = -7;



export default memo(function MessageIncoming(props: ThreeElements['mesh'] & { endPoint: [number, number, number], onVmContact: Function, gameOver: boolean, color: string }) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const endPoint = props.endPoint;
  useFrame((state, delta) => {
    if (!props.gameOver) {
      meshRef.current.rotation.x += delta * 2
      meshRef.current.rotation.y += delta / 2
    }
    const endingPointX = endPoint[0];
    if (meshRef.current.position.z > 0) {
      if (meshRef.current.position.y < playerEndYPosition) {
        // Has reached the bottom of the VM, ready to be reset
        if (!props.gameOver) {
          meshRef.current.position.y = 10 + 3 * Math.random();
          const isPlayer1 = endingPointX < 0;
          meshRef.current.position.x = (isPlayer1 ? loadBalancerXPosition + Math.random() - 0.6 : -loadBalancerXPosition - Math.random() + 0.6);
          meshRef.current.position.z = startingBoxZ;
        } else {
          // if game is over, incoming message should stay hidden under the VM
          meshRef.current.scale.x = 0.0001
          meshRef.current.scale.y = 0.0001
          meshRef.current.scale.z = 0.0001
        }
      } else {
        meshRef.current.position.y -= delta * 4
      }
    } else if (meshRef.current.position.y < playerMidYPosition) {
      // z is used to track if onVmContact has already been called
      // and only call onVmContact one time
      // if z is greater than 0, it has been
      meshRef.current.position.y -= delta * 4
      meshRef.current.position.z = 0.01;
      props.onVmContact();
    } else if (meshRef.current.position.y < playerMidYPosition + 0.1) {
      // about to reach midpoint, go immediately to final x position before dropping
      meshRef.current.position.x = endingPointX
      meshRef.current.position.y -= delta
    } else if (meshRef.current.position.y < playerMidYPosition + 0.2) {
      // a little time left before dropping
      meshRef.current.position.x = endingPointX * 0.3 + meshRef.current.position.x * 0.7
      meshRef.current.position.y -= delta
    } else if (meshRef.current.position.y < playerMidYPosition + 0.5) {
      // just started being directed to a vm drop location
      meshRef.current.position.x = endingPointX * 0.1 + meshRef.current.position.x * 0.9
      meshRef.current.position.y -= delta
    } else if (meshRef.current.position.z < 0 && meshRef.current.position.y < 3) {
      // getting close to the load balancer on the y axis
      // bring the incoming message closer on the z axis
      meshRef.current.position.y -= delta * 2
      const newZ = meshRef.current.position.z + delta * 5;
      meshRef.current.position.z = newZ > 0 ? 0 : newZ;
    } else if (meshRef.current.position.z < 0 && meshRef.current.position.y < 5) {
      // pick up speed toward the load balancer
      meshRef.current.position.y -= delta * 2
      const newZ = meshRef.current.position.z + delta * 2;
      meshRef.current.position.z = newZ > 0 ? 0 : newZ;
    } else if (meshRef.current.position.z < 0 && meshRef.current.position.y < 10) {
      // just entering the canvas, start moving toward the load balancer
      meshRef.current.position.y -= delta * 2
      const newZ = meshRef.current.position.z + delta / 2;
      meshRef.current.position.z = newZ > 0 ? 0 : newZ;
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
      <meshStandardMaterial color={props.color} />
    </mesh>
  )
});
