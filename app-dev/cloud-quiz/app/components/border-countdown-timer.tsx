"use client"

import { Game, gameStates } from "@/app/types";
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
    // save intervalId to clear the interval when the
    // component re-renders
    const intervalId = setInterval(() => {

      const {
        isAFullThreeSecondsOverTime,
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

      // smooth counting is delayed briefly to allow the timer
      // to get to the right place before animating
      if (!isSmoothCounting) {
        setTimeout(() => setIsSmoothCounting(true), 100);
      }

      // this code is here as a backup in case the questions stop advancing
      // it is possible that the server has stopped
      // prompt the server to move to the next question and start counting again
      const nudgeGame = async () => {
        await fetch('/api/nudge-game', {
          method: 'POST',
          body: JSON.stringify({ gameId: gameRef.id }),
        }).catch(error => {
          console.error({ error })
        });
      }
      if (isAFullThreeSecondsOverTime) {
        nudgeGame();
      }
    }, 100);

    // clear interval on re-render to avoid memory leaks
    return () => clearInterval(intervalId);
  }, [timeLeft, game.state, game.timePerAnswer, game.timePerQuestion]);

  // this is the percent of the entire animation that has completed
  // the `+ 1` allows the animation to target where it "should" be in one second
  const animationCompletionPercentage = (timeToCountDown - timeLeft + 1) / timeToCountDown;

  const css = `
  div.timer {
    background: none;
    box-sizing: border-box;
    padding: 2em 4em;
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
    border-top: ${Math.max(Math.min((animationCompletionPercentage * 400) * 100000000, 8), 0)}px solid var(--google-cloud-red);
    border-right: ${Math.max(Math.min((animationCompletionPercentage * 400 - 100) * 100000000, 8), 0)}px solid var(--google-cloud-blue);
    top: 0;
    left: 0;
    width: ${Math.max(Math.min(animationCompletionPercentage * 400, 100), 0)}%;
    height: ${Math.max(Math.min(animationCompletionPercentage * 400 - 100, 100), 0)}%;
  }
  
  div.timer.down::after {
    border-bottom: ${Math.max(Math.min((animationCompletionPercentage * 400 - 200) * 10000000000, 8), 0)}px solid var(--google-cloud-green);
    border-left: ${Math.max(Math.min((animationCompletionPercentage * 400 - 300) * 10000000000, 8), 0)}px solid var(--google-cloud-yellow);
    bottom: 0;
    right: 0;
    width: ${Math.max(Math.min(animationCompletionPercentage * 400 - 200, 100), 0)}%;
    height: ${Math.max(Math.min(animationCompletionPercentage * 400 - 300, 100), 0)}%;
  }
  
  div.timer.up::before {
    border-top: ${Math.max(Math.min((400 - animationCompletionPercentage * 400) * 100000000, 8), 0)}px solid var(--google-cloud-red);
    border-right: ${Math.max(Math.min((300 - animationCompletionPercentage * 400) * 100000000, 8), 0)}px solid var(--google-cloud-blue);
    top: 0;
    left: 0;
    width: ${Math.max(Math.min(400 - animationCompletionPercentage * 400, 100), 0)}%;
    height: ${Math.max(Math.min(300 - animationCompletionPercentage * 400, 100), 0)}%;
  }
  
  div.timer.up::after {
    border-bottom: ${Math.max(Math.min((200 - animationCompletionPercentage * 400) * 100000000, 8), 0)}px solid var(--google-cloud-green);
    border-left: ${Math.max(Math.min((100 - animationCompletionPercentage * 400) * 100000000, 8), 0)}px solid var(--google-cloud-yellow);
    bottom: 0;
    right: 0;
    width: ${Math.max(Math.min(200 - animationCompletionPercentage * 400, 100), 0)}%;
    height: ${Math.max(Math.min(100 - animationCompletionPercentage * 400, 100), 0)}%;
  }
  `;

  return (
    <>
      <div className={`timer ${isSmoothCounting ? 'smooth-counting' : ''} ${countDirection}`}>
        <div className="float-right -mt-4 -mr-12 bg-gray-100 py-1 px-2">
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
