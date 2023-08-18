/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

"use client"

import { Game } from "@/app/types";
import { DocumentReference, Timestamp } from "firebase/firestore";
import { useEffect, useState } from "react";
import { timeCalculator } from "../lib/time-calculator";

export default function BorderCountdownTimer({ game, children, gameRef }: { game: Game, children: React.ReactNode, gameRef: DocumentReference }) {
  const [timeToCountDown, setTimeToCountDown] = useState(game.timePerQuestion);
  const [displayTime, setDisplayTime] = useState(game.timePerQuestion);
  const [countDirection, setCountDirection] = useState<"down" | "up">("down");
  const [localCounter, setLocalCounter] = useState<number>(0);

  useEffect(() => {
    const {
      timeLeft,
      timeToCountDown,
      displayTime,
      countDirection,
    } = timeCalculator({
      currentTimeInMillis: Timestamp.now().toMillis(),
      game,
    });

    setTimeToCountDown(timeToCountDown);
    setDisplayTime(displayTime);
    setCountDirection(countDirection);

    const nudgeGame = async () => {
      await fetch('/api/nudge-game', {
        method: 'POST',
        body: JSON.stringify({ gameId: gameRef.id }),
      }).catch(error => {
        console.error({ error })
      });
    }

    // nudge every three seconds after time has expired
    if (timeLeft % 3 < -2) {
      nudgeGame();
    }
  }, [localCounter, game, gameRef.id])

  useEffect(() => {
    // save intervalIdOne to clear the interval when the
    // component re-renders
    const timeoutIdOne = setTimeout(() => {
      setLocalCounter(localCounter + 1);
    }, 1000);

    // clear interval on re-render to avoid memory leaks
    return () => clearTimeout(timeoutIdOne);
  }, [localCounter]);

  const limitPercents = (num: number) => Math.max(Math.min(num, 100), 0);

  // this is the percent of the entire animation that has completed
  // the `+ 1` allows the animation to target where it "should" be in one second
  const animationCompletionPercentage = limitPercents((timeToCountDown - displayTime + 1) / (timeToCountDown) * 100);

  const topBorderPercentage = limitPercents(countDirection === "down" ? animationCompletionPercentage * 4 : 400 - animationCompletionPercentage * 4);
  const rightBorderPercentage = limitPercents(countDirection === "down" ? animationCompletionPercentage * 4 - 100 : 300 - animationCompletionPercentage * 4);
  const bottomBorderPercentage = limitPercents(countDirection === "down" ? animationCompletionPercentage * 4 - 200 : 200 - animationCompletionPercentage * 4);
  const leftBorderPercentage = limitPercents(countDirection === "down" ? animationCompletionPercentage * 4 - 300 : 100 - animationCompletionPercentage * 4);




  return (
    <>
      <div className={`relative p-4 h-[50dvh] overflow-hidden`}>
        <div className="timer-top-border absolute top-0 left-0 bg-[var(--google-cloud-red)]" style={{ height: '8px', width: `${topBorderPercentage}%`, transition: 'width 1s linear' }} />
        <div className="timer-right-border absolute top-0 right-0 bg-[var(--google-cloud-blue)]" style={{ height: `${rightBorderPercentage}%`, width: '8px', transition: 'height 1s linear' }} />
        <div className="timer-bottom-border absolute bottom-0 right-0 bg-[var(--google-cloud-green)]" style={{ height: '8px', width: `${bottomBorderPercentage}%`, transition: 'width 1s linear' }} />
        <div className="timer-left-border absolute bottom-0 left-0 bg-[var(--google-cloud-yellow)]" style={{ height: `${leftBorderPercentage}%`, width: '8px', transition: 'height 1s linear' }} />
        <div className="h-full w-full border-8 border-transparent">
          <div className="bg-gray-100 py-1 px-2 float-right">
            {displayTime < 10 && '0'}
            {displayTime}
          </div>
          {children}
        </div>
      </div>
    </>
  )
}
