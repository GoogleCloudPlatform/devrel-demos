'use client'

import React, { useEffect, useState } from 'react'
import { getRawStats } from '@/app/actions'

export default function Stats() {
  const [timer, setTimer] = useState(-5);
  const [vmRawStatsStringified, setVmRawStatsStringified] = useState('')
  const [playerOneScore, setPlayerOneScore] = useState(0);
  const [playerTwoScore, setPlayerTwoScore] = useState(0);

  useEffect(() => {
    const getVMStatus = async () => {
      var startTime = performance.now()
      const rawStats = await getRawStats(localStorage.getItem("secretPassword") || '');
      var endTime = performance.now()
      setPlayerOneScore(rawStats.GAME_SCORE_PLAYER);
      setPlayerTwoScore(rawStats.GAME_SCORE_GCLB);
      setVmRawStatsStringified(JSON.stringify(rawStats, function (k, v) {
        if (v instanceof Array)
          return JSON.stringify(v);
        return v;
      }, 2).replaceAll('\"', '').replaceAll('\\', '').replaceAll('\{', '').replaceAll('\}', ''));
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

  return (
    <pre>
      {vmRawStatsStringified}
    </pre>
  );
}
