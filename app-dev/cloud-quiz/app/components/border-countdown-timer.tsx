"use client"

import { Game, gameStates } from "@/app/types";
import { DocumentReference, Timestamp } from "firebase/firestore";
import { useEffect, useState } from "react";
import { timeCalculator } from "../lib/time-calculator";

export default function BorderCountdownTimer({ game, children, gameRef }: { game: Game, children: React.ReactNode, gameRef: DocumentReference }) {
  const [timeToCountDown, setTimeToCountDown] = useState(game.timePerQuestion);
  const [timeLeft, setTimeLeft] = useState(game.timePerQuestion);
  const [countDirection, setCountDirection] = useState<string>("stopped");

  useEffect(() => {
    // save intervalId to clear the interval when the
    // component re-renders
    const intervalId = setInterval(() => {
      const {
        timeElapsed,
        timeToShowCurrentQuestionAnswer,
        timeToStartNextQuestion,
        isAFullThreeSecondsOverTime,
      } = timeCalculator({
        currentTimeInSeconds: Timestamp.now().seconds,
        game,
      });

      if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
        setTimeLeft(Math.floor(timeToShowCurrentQuestionAnswer - timeElapsed));
      } else {
        setTimeLeft(Math.floor(timeToStartNextQuestion - timeElapsed));
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
    }, 1000);

    // clear interval on re-render to avoid memory leaks
    return () => clearInterval(intervalId);
  }, [timeLeft]);

  useEffect(() => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
      setCountDirection("down");
      setTimeToCountDown(game.timePerQuestion);
      setTimeLeft(game.timePerQuestion);
    } else if (game.state === gameStates.SHOWING_CORRECT_ANSWERS) {
      setCountDirection("up");
      setTimeToCountDown(game.timePerAnswer);
      setTimeLeft(game.timePerAnswer);
    }
  }, [game.state, game.timePerAnswer, game.timePerQuestion]);

  const displayTime = Math.max(timeLeft, 0);

  const css = `
  div.timer {
    background: none;
    border: 0;
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
    width: 100%;
    height: 100%;
  }
  
  div.timer.counting::before,
  div.timer.counting::after {
    border: 8px solid transparent;
    width: 0;
    height: 0;
  }
  
  div.timer.counting::before,
  div.timer.counting::after {
    top: 0;
    left: 0;
  }
  
  div.timer.counting.down::before,
  div.timer.counting.down::after {
    width: 100%;
    height: 100%;
  }
  
  /* Top and right timer bars going out */
  div.timer.counting.down::before {
    border-top-color: var(--google-cloud-red);
    border-right-color: var(--google-cloud-blue);
    transition: width ${0.50 * timeToCountDown}s linear, height ${0.50 * timeToCountDown}s linear ${0.50 * timeToCountDown}s;
  }
  
  /* Bottom and left timer bars going out */
  div.timer.counting.down::after {
    border-bottom-color: var(--google-cloud-green);
    border-left-color: var(--google-cloud-yellow);
    transition: height ${0.50 * timeToCountDown}s linear, width ${0.50 * timeToCountDown}s linear ${0.50 * timeToCountDown}s;
  }
  
  /* Top and right timer bars going in */
  div.timer.counting::before {
    border-top-color: var(--google-cloud-red);
    border-right-color: var(--google-cloud-blue);
    transition: height ${0.50 * timeToCountDown}s linear, width ${0.50 * timeToCountDown}s linear ${0.50 * timeToCountDown}s;
  }
  
  /* Top and right timer bars going in */
  div.timer.counting::after {
    border-bottom-color: var(--google-cloud-green);
    border-left-color: var(--google-cloud-yellow);
    transition: width ${0.50 * timeToCountDown}s linear, height ${0.50 * timeToCountDown}s linear ${0.50 * timeToCountDown}s;
  }
  `;

  return (
    <>
      <div className={`timer counting ${countDirection}`}>
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
