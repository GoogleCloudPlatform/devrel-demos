"use client"

import React, { memo, useEffect, useState } from "react"

export default memo(function Results({
  playerOneScore,
  playerTwoScore,
  playerName,
}: {
  playerOneScore: number
  playerTwoScore: number
  playerName: string
}) {
  const [showResults, setShowResults] = useState(false)
  // Store final scores when component mounts to prevent updates
  const [finalPlayerOneScore] = useState(playerOneScore)
  const [finalPlayerTwoScore] = useState(playerTwoScore)
  
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.code === "KeyS") {
        window.location.reload()
      }
    }
    const timeout = setTimeout(() => setShowResults(true), 200)
    window.addEventListener("keydown", handleKeyDown)

    return () => {
      clearTimeout(timeout)
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [])

  const playerEfficiency = `${finalPlayerTwoScore > 0 ? (Number(finalPlayerOneScore) / Number(finalPlayerTwoScore) * 100).toFixed(0) : `00`}%`

  return (
    <div
      className={`flex flex-col items-center justify-center transition-opacity fixed top-0 left-0 right-0 bottom-0 bg-[#2B374B] text-white duration-1000 ${
        showResults ? "opacity-100" : "opacity-0"
      }`}
    >
      {/* Game Over Title */}
      <div className="mb-10 text-7xl text-red-500 font-bold tracking-widest" style={{ fontFamily: "Jersey15, sans-serif" }}>
        GAME OVER!
      </div>

      {/* Scores Section */}
      <div className="flex items-center justify-center text-center text-white">
        {/* Player Score */}
        <div className="mr-16">
          <p className="text-gray-400 text-3xl tracking-wider" style={{ fontFamily: "Jersey15, sans-serif" }}>
            YOUR SCORE
          </p>
          <p className="text-8xl font-bold" style={{ fontFamily: "Jersey15, sans-serif" }}>
            {finalPlayerOneScore}
          </p>
        </div>

        {/* Vertical Divider */}
        <div className="h-32 w-2 bg-yellow-400"></div>

        {/* GLB Score */}
        <div className="ml-16">
          <p className="text-gray-400 text-3xl tracking-wider" style={{ fontFamily: "Jersey15, sans-serif" }}>
            GLB SCORE
          </p>
          <p className="text-8xl font-bold" style={{ fontFamily: "Jersey15, sans-serif" }}>
            {finalPlayerTwoScore}
          </p>
        </div>
      </div>

      {/* Performance Message */}
      <div className="bg-white text-[#2B374B] text-4xl mt-10 px-10 py-6 shadow-lg text-center " style={{ fontFamily: "Jersey15, sans-serif" }}>
        YOU PERFORMED{" "}
        <span className="text-blue-500 text-4xl">{playerEfficiency}</span> AS WELL AS THE <br />GOOGLE CLOUD LOAD BALANCER
      </div>

      {/* Press S to Retry */}
      <div className="flex items-center justify-center mt-12 text-[#4CCF6F] text-5xl tracking-wide" style={{ fontFamily: "Jersey15, sans-serif" }}>
        PRESS
        <span className="mx-3 px-4 py-1 bg-gray-700 text-green-400 text-5xl rounded-md border border-white shadow-md">
          S
        </span>
        TO RETRY
      </div>
    </div>
  )
})