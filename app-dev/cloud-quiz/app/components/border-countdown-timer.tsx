"use client"

import { Game, gameStates } from "@/app/types";
import { useEffect, useState } from "react";

export default function BorderCountdownTimer({ game, children }: { game: Game, children: React.ReactNode }) {
  const [timeToCountDown, setTimeToCountDown] = useState(game.timePerQuestion);
  const [timeLeft, setTimeLeft] = useState(game.timePerQuestion);
  const [countDirection, setCountDirection] = useState<string>("stopped");

  useEffect(() => {
    // save intervalId to clear the interval when the
    // component re-renders
    const intervalId = setInterval(() => {
      if (timeLeft < 0) {
        setTimeLeft(0);
      } else {
        setTimeLeft(timeLeft - 1);
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
  }, [game.state]);


  const css = `
  div.timer {
    background: none;
    border: 0;
    box-sizing: border-box;
    margin: 1em;
    padding: 2em 4em;
    box-shadow: inset 0 0 0 2px #000000;
    color: #000000;
    font-size: inherit;
    font-weight: 700;
    position: relative;
    vertical-align: middle;
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
  
  div.timer.counting::before {
    top: 0;
    left: 0;
  }
  
  div.timer.counting::after {
    bottom: 0;
    right: 0;
  }
  
  div.timer.counting.down::before,
  div.timer.counting.down::after {
    width: 100%;
    height: 100%;
  }
  
  div.timer.counting.down::before {
    border-top-color: #db3236;
    border-right-color: #4885ed;
    transition: width ${timeToCountDown / 4}s ease-out, height ${timeToCountDown / 4}s ease-out ${timeToCountDown / 4}s;
  }
  
  div.timer.counting.down::after {
    border-bottom-color: #3cba54;
    border-left-color: #f4c20d;
    transition: border-color 0s ease-out ${timeToCountDown / 2}s, width ${timeToCountDown / 4}s ease-out ${timeToCountDown / 2}s, height ${timeToCountDown / 4}s ease-out ${timeToCountDown / 4 * 3}s;
  }
  
  div.timer.counting::before {
    border-top-color: #db3236;
    border-right-color: #4885ed;
    transition: height ${timeToCountDown / 4}s ease-out, width ${timeToCountDown / 4}s ease-out ${timeToCountDown / 4}s;
  }
  
  div.timer.counting::after {
    border-bottom-color: #3cba54;
    border-left-color: #f4c20d;
    transition: border-color 0s ease-out ${timeToCountDown / 2}s, height ${timeToCountDown / 4}s ease-out ${timeToCountDown / 2}s, width ${timeToCountDown / 4}s ease-out ${timeToCountDown / 4 * 3}s;
  }
  `;

  return (
    <>
      <div className={`timer counting ${ countDirection }`}>
        {children}
      </div>
      <style>
        {css}
      </style>
    </>
  )
}
