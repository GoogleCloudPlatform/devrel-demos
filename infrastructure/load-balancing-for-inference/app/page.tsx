"use client"

import { useState } from "react"
import Play from "@/components/Play"
import StartButton from "@/components/StartButton"
import Image from "next/image"
import Play3D from "@/components/play3d"; // 3D effect for home screen

export default function Home() {
  const [showPlayComponent, setShowPlayComponent] = useState<boolean>(false)

  return (
    <div className="relative min-h-screen bg-[#FBBC04]">
      {/* Show Play3D only on Home Screen, Hide it when game starts */}
      {!showPlayComponent && (
        <div className="absolute top-0 left-0 w-full h-full z-0">
          <Play3D /> 
        </div>
      )}

      {/* Game UI: Only Show Play when "S" is Pressed */}
      {showPlayComponent ? (
        <Play />
      ) : (
        <main className="relative flex flex-col min-h-screen items-center justify-between p-8 z-10">
          {/* Title Image */}
          <div className="w-full max-w-4xl relative mt-2 -mb-8 z-20">
            <Image
              src="/LB-blitz title.png"
              alt="Load Balancing Blitz"
              width={800}
              height={200}
              className="w-full h-auto"
              priority
            />
          </div>

          {/* Instruction Box */}
          <div className="bg-[#FFF8E7] rounded-xl p-6 max-w-3xl relative z-10"> 
            <p className="text-gray-800 text-center mb-2">
              Press 1, 2, 3, and 4 to distribute the incoming requests across the four virtual machines.
            </p>
            <p className="text-gray-800 text-center font-medium">
              <span className="font-bold">Hint:</span> Keep moving! Be careful not to direct all of the requests to a single machine.
            </p>
          </div>

          {/* Start Button */}
          <StartButton onClick={() => setShowPlayComponent(true)} className="z-20" />

          <div className="h-24" />
        </main>
      )}
    </div>
  )
}
