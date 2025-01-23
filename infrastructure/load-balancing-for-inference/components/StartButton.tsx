'use client'

import React, { useEffect, useState } from 'react'
import { getRawStats } from '@/app/actions'

export default function StartButton({ onClick }: { onClick: Function }) {
  const [timer, setTimer] = useState(-5);
  const [gameIsInProgress, setGameIsInProgress] = useState(true);
  const [timeRemaining, setTimeRemaining] = useState(61);

  useEffect(() => {
    const getVMStatus = async () => {
      var startTime = performance.now()
      const rawStats = await getRawStats(localStorage.getItem("secretPassword") || '');
      var endTime = performance.now()
      setTimeRemaining(61 - rawStats.GAME_CURRENT_TIME);
      setGameIsInProgress(rawStats.GAME_IS_IN_PROGRESS && rawStats.GAME_CURRENT_TIME < 61);
      const duration = Math.floor(endTime - startTime);
      console.log(`Call to vmStatuses took ${duration} milliseconds`);
    }
    getVMStatus();
  }, [timer]);

  useEffect(() => {
    //Implementing the setInterval method
    const interval = setInterval(() => {
      setTimer(timer + 1);
    }, 1000);

    //Clearing the interval
    return () => clearInterval(interval);
  }, [timer]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      switch (event.code) {
        case 'KeyS':
          onClick(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClick, gameIsInProgress]);

  return (
    <>
      {gameIsInProgress ? (
        <button
          onClick={() => { }}
          className="group rounded-lg border px-5 py-4 transition-colors hover:bg-gray-100"
        >
          <h2 className={`mb-3 text-5xl font-mono`}>
            Game Already In Progress
          </h2>
          <h2 className={`mb-3 text-3xl font-mono`}>
            Check Back In {Math.ceil(timeRemaining)} seconds
          </h2>
        </button>
      ) : (
        <button
          onClick={() => onClick()}
          className="group rounded-lg border px-5 py-4 transition-colors hover:bg-gray-100"
        >
          <h2 className={`mb-3 text-5xl font-mono`}>
            Press S to start
            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
              -&gt;
            </span>
          </h2>
        </button>
      )}
    </>
  );
}
