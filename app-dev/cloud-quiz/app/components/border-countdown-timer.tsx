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
  const [timeLeft, setTimeLeft] = useState(game.timePerQuestion);
  const [isSmoothCounting, setIsSmoothCounting] = useState<Boolean>(false);
  const [countDirection, setCountDirection] = useState<"down" | "up">("down");

  useEffect(() => {
    // save intervalIdOne to clear the interval when the
    // component re-renders
    const timeoutIdOne = setTimeout(() => {

      const {
        timeLeft,
        timeToCountDown,
        displayTime,
        countDirection,
      } = timeCalculator({
        currentTimeInMillis: Timestamp.now().toMillis(),
        game,
      });

      setTimeLeft(timeLeft);
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
      if (Math.floor((timeLeft * 10 % 39)) < -38) {
        nudgeGame();
      }

      setTimeout(() => setIsSmoothCounting(timeLeft > -2 && document.visibilityState === 'visible'), 1);

    }, 100);

    // clear interval on re-render to avoid memory leaks
    return () => { clearTimeout(timeoutIdOne) };

    // including exhaustive deps (specifically `game`) makes the re-render take far too long
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeLeft]);

  // this is the percent of the entire animation that has completed
  // the `+ 1` allows the animation to target where it "should" be in one second
  const animationCompletionPercentage = (timeToCountDown - timeLeft + 1) / timeToCountDown * 100;

  const css = `
  div.timer {
    background: none;
    box-sizing: border-box;
    padding: 1em 2em;
    box-shadow: inset 0 0 0 2px #F3F4F6;
    color: #000000;
    font-size: inherit;
    font-weight: 700;
    position: relative;
    vertical-align: middle;
    height: 50vh;
  }
  
  div.timer::before,
  div.timer::after {
    box-sizing: inherit;
    content: "";
    position: absolute;
    border: 8px solid transparent;
  }
  
  div.timer.smooth-counting::before,
  div.timer.smooth-counting::after {
    transition: height 0.1s linear, width 0.1s linear, border 0.1s linear;
  }
  
  div.timer.down::before {
    border-top: ${animationCompletionPercentage > 0 ? '8' : '0'}px solid var(--google-cloud-red);
    border-right: ${animationCompletionPercentage > 25 ? '8' : '0'}px solid var(--google-cloud-blue);
    top: 0;
    left: 0;
    width: ${Math.max(Math.min(animationCompletionPercentage * 4, 100), 0)}%;
    height: ${Math.max(Math.min(animationCompletionPercentage * 4 - 100, 100), 0)}%;
  }
  
  div.timer.down::after {
    border-bottom: ${animationCompletionPercentage > 50 ? '8' : '0'}px solid var(--google-cloud-green);
    border-left: ${animationCompletionPercentage > 75 ? '8' : '0'}px solid var(--google-cloud-yellow);
    bottom: 0;
    right: 0;
    width: ${Math.max(Math.min(animationCompletionPercentage * 4 - 200, 100), 0)}%;
    height: ${Math.max(Math.min(animationCompletionPercentage * 4 - 300, 100), 0)}%;
  }
  
  div.timer.up::before {
    border-top: ${animationCompletionPercentage < 100 ? '8' : '0'}px solid var(--google-cloud-red);
    border-right: ${animationCompletionPercentage < 75 ? '8' : '0'}px solid var(--google-cloud-blue);
    top: 0;
    left: 0;
    width: ${Math.max(Math.min(400 - animationCompletionPercentage * 4, 100), 0)}%;
    height: ${Math.max(Math.min(300 - animationCompletionPercentage * 4, 100), 0)}%;
  }
  
  div.timer.up::after {
    border-bottom: ${animationCompletionPercentage < 50 ? '8' : '0'}px solid var(--google-cloud-green);
    border-left: ${animationCompletionPercentage < 25 ? '8' : '0'}px solid var(--google-cloud-yellow);
    bottom: 0;
    right: 0;
    width: ${Math.max(Math.min(200 - animationCompletionPercentage * 4, 100), 0)}%;
    height: ${Math.max(Math.min(100 - animationCompletionPercentage * 4, 100), 0)}%;
  }
  `;

  return (
    <>
      <div className={`timer ${isSmoothCounting ? 'smooth-counting' : ''} ${countDirection}`}>
        <div className="float-right -mt-1 -mr-4 ml-1 bg-gray-100 py-1 px-2">
          {displayTime < 10 && '0'}
          {displayTime}
        </div>
        {children}
      </div>
      <style>
        {css}
      </style>
    </>
  )
}
