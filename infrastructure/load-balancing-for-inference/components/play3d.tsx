"use client"

import { useRef, useState, useEffect } from "react"
import { Canvas, useFrame } from "@react-three/fiber"
import { BoxGeometry, type Group, MeshBasicMaterial, Vector3 } from "three"

function MovingBox({ startPosition, delay = 0 }: { startPosition: [number, number, number], delay?: number }) {
  const ref = useRef<Group>(null)
  const [active, setActive] = useState(delay === 0)

  // Calculate direction vector once
  const [direction] = useState(() => {
    // Create normalized direction vector from center to startPosition
    const dirVector = new Vector3(startPosition[0], startPosition[1], 0).normalize()
    const speed = 0.04 + Math.random() * 0.03 // Adjusted base speed
    return [
      dirVector.x * speed,
      dirVector.y * speed,
      0.06 + Math.random() * 0.025, // Z movement
    ] as [number, number, number]
  })

  // Activate the cube after its delay
  useEffect(() => {
    if (delay > 0) {
      const timer = setTimeout(() => {
        setActive(true)
      }, delay)
      return () => clearTimeout(timer)
    }
  }, [delay])

  // Smooth movement in the animation loop
  useFrame((state, delta) => {
    if (!ref.current || !active) return

    // Cap delta to avoid large jumps on slow frames or tab switching
    const smoothDelta = Math.min(delta, 0.05)
    const moveSpeed = 45 // Tweak to taste

    // Frame-rate–independent movement
    ref.current.position.x += direction[0] * smoothDelta * moveSpeed
    ref.current.position.y += direction[1] * smoothDelta * moveSpeed
    ref.current.position.z += direction[2] * smoothDelta * moveSpeed
  })

  // If not active, render invisible cube to keep consistent instancing
  if (!active) {
    return (
      <group ref={ref} position={startPosition} visible={false}>
        <mesh>
          <boxGeometry args={[0.3, 0.3, 0.3]} />
          <meshBasicMaterial color="#FADF6B" />
        </mesh>
      </group>
    )
  }

  return (
    <group ref={ref} position={startPosition}>
      {/* Main 3D Box */}
      <mesh>
        <boxGeometry args={[0.3, 0.3, 1.3]} />
        <meshBasicMaterial
          color="#FADF6B"
          transparent={true}
          opacity={0.9}
          toneMapped={false}
        />
      </mesh>

      {/* Border Outline */}
      <lineSegments>
        <edgesGeometry attach="geometry" args={[new BoxGeometry(0.3, 0.3, 1.3)]} />
        <lineBasicMaterial 
          attach="material" 
          color="#e3a507"
          linewidth={3}
        />
      </lineSegments>
    </group>
  )
}

export default function Play3D() {
  const [cubes, setCubes] = useState<Array<{
    key: string
    startPosition: [number, number, number]
    delay: number
  }>>([])

  const totalCreatedRef = useRef(0)

  // Function to create a new cube
  const createNewCube = () => {
    totalCreatedRef.current += 1
    const id = totalCreatedRef.current
    
    // Random distribution patterns
    let angle, dirX, dirY, distance
    const pattern = id % 4
    
    if (pattern === 0) {
      // Evenly distributed rays
      angle = (id % 72) * ((Math.PI * 2) / 72)
      distance = 0.01 + Math.random() * 0.02
    } else if (pattern === 1) {
      // Randomly distributed
      angle = Math.random() * Math.PI * 2
      distance = 0.01 + Math.random() * 0.03
    } else {
      // Concentrated in quadrants
      angle =
        ((Math.floor(id / 10) % 4) * Math.PI) / 2 + Math.random() * (Math.PI / 4)
      distance = 0.01 + Math.random() * 0.02
    }
    
    dirX = Math.cos(angle)
    dirY = Math.sin(angle)
    
    return {
      key: `cube-${id}`,
      startPosition: [
        dirX * distance,
        dirY * distance,
        -12 - Math.random() * 4
      ] as [number, number, number],
      delay: Math.random() * 150
    }
  }

  useEffect(() => {
    // Set initial cubes
    const initialCubes = Array(60).fill(0).map(() => createNewCube())
    setCubes(initialCubes)
    
    // Add new cubes at a slightly lower rate
    const interval = setInterval(() => {
      setCubes(prev => {
        // Create a small batch each time
        const newCount = 3 + Math.floor(Math.random() * 2)
        const newCubes = Array(newCount).fill(0).map(() => createNewCube())
        
        const combinedCubes = [...prev, ...newCubes]
        // Limit total cubes to reduce overhead
        if (combinedCubes.length > 200) {
          return combinedCubes.slice(combinedCubes.length - 180)
        }
        return combinedCubes
      })
    }, 80) // Spawn cubes every 80ms instead of 50ms

    return () => clearInterval(interval)
  }, [])

  return (
    <Canvas
      camera={{ position: [0, 0, 6], fov: 60 }}
      frameloop="always"
      gl={{
        antialias: true,
        powerPreference: "high-performance"
      }}
      // Optional: Let ThreeJS adjust detail for performance
      // performance={{ min: 0.5 }}
    >
      <color attach="background" args={["#FFB800"]} />
      <ambientLight intensity={1.5} />
      <directionalLight position={[3, 3, 5]} intensity={1.5} color="#FFFFFF" />
      {cubes.map(({ key, startPosition, delay }) => (
        <MovingBox key={key} startPosition={startPosition} delay={delay} />
      ))}
    </Canvas>
  )
}
