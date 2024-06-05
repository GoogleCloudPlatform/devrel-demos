'use client'

import React, { memo, useEffect, useState } from 'react'

export default memo(function Results({ playerOneScore, playerTwoScore }: { playerOneScore: number, playerTwoScore: number }) {
  const [showResults, setShowResults] = useState(false);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      switch (event.code) {
        case 'KeyS':
          window.location.reload();
      }
    };
    const timeout = setTimeout(() => setShowResults(true), 200);
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      clearTimeout(timeout);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const playerEfficiency = `${playerTwoScore > 0 ? (Number(playerOneScore) / Number(playerTwoScore) * 100).toFixed(1) : `00.0`}%`;


  return (
    < div className={`flex flex-col items-center justify-center transition-opacity fixed top-0 left-0 right-0 bottom-0 bg-gradient-to-t from-white via-white to-transparent duration-1000 ${showResults ? 'opacity-100' : 'opacity-0'}`
    }>
      <div>
        <span className="text-7xl font-mono">Game Over</span>
      </div>
      <div className='text-7xl font-mono m-16'>
        <table className=''>
          <tbody>
            <tr>
              <td>Your Score</td>
              <td className='text-right pl-16 font-mono'>{playerOneScore}</td>
            </tr>
            <tr>
              <td>GLB Score</td>
              <td className='text-right pl-16 font-mono'>{playerTwoScore}</td>
            </tr>
            <tr className="text-2xl">
              <td colSpan={2} className='text-center pt-4'>
                You performed {playerEfficiency} as well as the Google Cloud Load Balancer.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="flex flex-col items-center justify-between">
        <a
          href="/"
          className="group rounded-lg border px-5 py-4 transition-colors hover:bg-gray-100"
        >
          <h2 className={`mb-3 text-5xl font-semibold`}>
            Press S to return home
            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
              -&gt;
            </span>
          </h2>
        </a>
      </div>
    </div >
  );
});
