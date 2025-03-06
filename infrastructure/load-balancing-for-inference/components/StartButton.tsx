"use client"

import { useEffect, useState } from "react"

export default function StartButton({ onClick, className }: { onClick: Function; className?: string }) {
  const [timer, setTimer] = useState(-5)
  const [gameIsInProgress, setGameIsInProgress] = useState(true)
  const [timeRemaining, setTimeRemaining] = useState(61)

  useEffect(() => {
    const getVMStatus = async () => {
      var startTime = performance.now()
      const rawStats = {
        GAME_CURRENT_TIME: 61 - timer,
        GAME_SCORE_PLAYER: 0,
        GAME_SCORE_GCLB: 0,
        GAME_IS_IN_PROGRESS: true,
      }
      var endTime = performance.now()
      setTimeRemaining(61 - rawStats.GAME_CURRENT_TIME)
      setGameIsInProgress(rawStats.GAME_IS_IN_PROGRESS && rawStats.GAME_CURRENT_TIME < 61)
      const duration = Math.floor(endTime - startTime)
      console.log(`Call to vmStatuses took ${duration} milliseconds`)
    }
    getVMStatus()
  }, [timer])

  useEffect(() => {
    // Implementing the setInterval method
    const interval = setInterval(() => {
      setTimer(timer + 1)
    }, 1000)

    // Clearing the interval
    return () => clearInterval(interval)
  }, [timer])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      switch (event.code) {
        case "KeyS":
          onClick(true)
      }
    }
    window.addEventListener("keydown", handleKeyDown)

    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onClick])

  return (
    <>
      {gameIsInProgress ? (
        <button 
          onClick={() => {}} 
          className={`bg-gray-300 text-gray-600 rounded-lg px-8 py-6 mt-4 transition-colors ${className}`}
        >
          <h2 className="mb-3 text-4xl font-mono">Game Already In Progress</h2>
          <h2 className="mb-3 text-2xl font-mono">Check Back In {Math.ceil(timeRemaining)} seconds</h2>
        </button>
      ) : (
        <button
  onClick={() => onClick()}
  className={`text-[#191919] tracking-widest text-5xl font-bold transform transition-transform hover:scale-105 ${className}`}
  style={{ fontFamily: "Jersey15, sans-serif", border: "none", background: "none", padding: "0" }}
>
  PRESS 
  <span 
    className="mx-4 px-3 inline-flex items-center justify-center bg-black text-[#FBBC04] text-5xl"
    style={{
      fontFamily: "Jersey15, sans-serif",
      padding: "1px 16px",  // Adjusted horizontal padding
      paddingLeft: "20px",  // Added left padding
      borderRadius: "8px",
      minWidth: "60px",     // Added fixed width
      height: "60px",       // Added fixed height
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center"
    }}
  >
    S
  </span>
  TO START
</button>
      )}
    </>
  )
}
