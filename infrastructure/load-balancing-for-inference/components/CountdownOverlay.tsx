"use client";
import Image from "next/image";

interface CountdownOverlayProps {
  timeElapsed: number;
  timeRemaining: number;
  playerOneScore: number;
  playerTwoScore: number;
}

/**
 * Displays:
 *  - A main countdown (60s) at the top center inside timer-box.png, once timeElapsed >= 0
 *  - The "Get Ready!" overlay if timeElapsed < 0 (unchanged)
 */
export default function CountdownOverlay({
  timeElapsed,
  timeRemaining,
  playerOneScore,
  playerTwoScore,
}: CountdownOverlayProps) {
  return (
    <>
     {/* Player One Name - Left Aligned */}
     {timeElapsed >= 0 && timeRemaining > 0 && (
        <div className="absolute top-20 left-10 z-50 text-[#2B374B] font-bold text-5xl" style={{ fontFamily: "Jersey15, sans-serif" }}>
          YOU
        </div>
      )}

      {/* Countdown Timer - Center Aligned */}
      {timeElapsed >= 0 && (
        <div
          className={`absolute top-20 left-1/2 transform -translate-x-1/2 z-50 transition-opacity duration-1000 ${
            timeRemaining > 0 && timeElapsed > -1 ? "opacity-100" : "opacity-0"
          }`}
        >
          <div className="relative" style={{ fontFamily: "Jersey15, sans-serif" }}>
            <Image
              src="/assets/timer-box.png"
              alt="Timer Box"
              width={78}
              height={60}
              priority
            />
            <span className="absolute inset-0 flex items-center justify-center text-5xl font-bold text-[#2B374B]">
              {timeRemaining}
            </span>
          </div>
        </div>
      )}

     {/* Player Two Name - Right Aligned */}
     {timeElapsed >= 0 && timeRemaining > 0 && (
        <div className="absolute top-20 right-10 z-50 text-[#2B374B] font-bold text-5xl" style={{ fontFamily: "Jersey15, sans-serif" }}>
          GOOGLE CLOUD LOAD BALANCER
        </div>
      )}

      {/* "GET READY!" OVERLAY if timeElapsed < 0 (unchanged) */}
      {timeElapsed < 0 && (
        <div
          className="absolute top-0 left-0 w-full h-full flex flex-col justify-center items-center bg-[#2B374B] text-white z-50"
          style={{ fontFamily: "Jersey15, sans-serif" }}
        >
          {/* Top Bar with Zigzag Divider */}
          <div
            className="absolute top-0 left-0 w-full flex h-20 text-white font-bold tracking-wider"
            style={{ fontFamily: "Jersey15, sans-serif" }}
          >
            {/* Left Side - Player Score */}
            <div className="w-1/2 bg-[#FFB800] flex justify-end items-center relative pr-2">
              <span className="text-6xl">0</span> {/* Example placeholder */}
            </div>

            {/* Right Side - Opponent Score */}
            <div className="w-1/2 bg-[#4285F4] flex justify-left items-center pl-2">
              <span className="text-6xl">0</span> {/* Example placeholder */}
            </div>
          </div>

          {/* Player Names Below the Top Bar */}
          <div
            className="absolute top-24 w-full flex justify-between px-20 text-white text-5xl font-bold"
            style={{ fontFamily: "Jersey15, sans-serif" }}
          >
            <span>YOU</span>
            <span>GOOGLE CLOUD LOAD BALANCER</span>
          </div>

          {/* Countdown Box UI */}
          <div className="relative flex flex-col items-center justify-center mt-24">
            <Image
              src="/countdown-box.png"
              alt="Countdown Box"
              width={240}
              height={240}
              priority
            />
            <span className="absolute text-[12rem] font-bold text-white leading-none">
              {timeElapsed < 0 ? Math.abs(timeElapsed) : "GO!"}
            </span>
          </div>

          {/* "Get Ready!" Text */}
          <p className="text-[#FFB800] text-[3rem] font-bold mt-14">
            GET READY!
          </p>
        </div>
      )}
    </>
  );
}
