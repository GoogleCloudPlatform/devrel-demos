"use client"

import { Game, gameStates } from "@/app/types";
import { useEffect, useState } from "react";

export default function CountdownTimer({ game }: { game: Game }) {
  const [timeLeft, setTimeLeft] = useState(game.timePerQuestion);

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
      setTimeLeft(game.timePerQuestion);
    }
  }, [game.state]);

  return (
    <>
      <input
        type="range"
        min="0"
        max={game.timePerQuestion}
        value={timeLeft}
        readOnly
      />
    </>
  )
}
