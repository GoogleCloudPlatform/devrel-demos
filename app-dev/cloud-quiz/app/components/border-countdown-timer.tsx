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
    width: 0;
    height: 0;
  }
  
  div.timer.counting::before,
  div.timer.counting::after {
    border: 8px solid transparent;
    transition: height 1s linear, width 1s linear, border 0.1s linear;
  }
  
  div.timer.counting.down::before {
    border-top: 8px solid var(--google-cloud-red);
    border-right: ${Math.max(Math.min(((timeToCountDown - displayTime + 1) / timeToCountDown * 400 - 100) * 100000000, 8),0)}px solid var(--google-cloud-blue);
    top: 0;
    left: 0;
    width: ${Math.max(Math.min((timeToCountDown - displayTime + 1) / timeToCountDown * 400, 100), 0)}%;
    height: ${Math.max(Math.min((timeToCountDown - displayTime + 1) / timeToCountDown * 400 - 100, 100),0)}%;
  }
  
  div.timer.counting.down::after {
    border-bottom: ${Math.max(Math.min(((timeToCountDown - displayTime + 1) / timeToCountDown * 400 - 200) * 10000000000, 8),0)}px solid var(--google-cloud-green);
    border-left: ${Math.max(Math.min(((timeToCountDown - displayTime + 1) / timeToCountDown * 400 - 300) * 10000000000, 8),0)}px solid var(--google-cloud-yellow);
    bottom: 0;
    right: 0;
    width: ${Math.max(Math.min((timeToCountDown - displayTime + 1) / timeToCountDown * 400 - 200, 100), 0)}%;
    height: ${Math.max(Math.min((timeToCountDown - displayTime + 1) / timeToCountDown * 400 - 300, 100),0)}%;
  }
  
  div.timer.counting.up::before {
    border-top: 8px solid var(--google-cloud-red);
    border-right: ${Math.max(Math.min((300 - (timeToCountDown - displayTime) / timeToCountDown * 400) * 100000000, 8), 0)}px solid var(--google-cloud-blue);
    top: 0;
    left: 0;
    width: ${Math.max(Math.min(400 - (timeToCountDown - displayTime + 1) / timeToCountDown * 400, 100), 0)}%;
    height: ${Math.max(Math.min(300 - (timeToCountDown - displayTime + 1) / timeToCountDown * 400, 100),0)}%;
  }
  
  div.timer.counting.up::after {
    border-bottom: ${Math.max(Math.min((200 - (timeToCountDown - displayTime) / timeToCountDown * 400) * 100000000, 8), 0)}px solid var(--google-cloud-green);
    border-left: ${Math.max(Math.min((100 - (timeToCountDown - displayTime) / timeToCountDown * 400) * 100000000, 8), 0)}px solid var(--google-cloud-yellow);
    bottom: 0;
    right: 0;
    width: ${Math.max(Math.min(200 - (timeToCountDown - displayTime + 1) / timeToCountDown * 400, 100), 0)}%;
    height: ${Math.max(Math.min(100 - (timeToCountDown - displayTime + 1) / timeToCountDown * 400, 100),0)}%;
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
