"use client"

import { Game } from "@/app/types";
import { useState, useEffect } from "react";

export default function CountdownTimer({ game }: { game: Game }) {
  const [timer, setTimer] = useState<number>(game.timePerQuestion);

  useEffect(() => {
    setTimer(game.timePerQuestion);
    const interval = setInterval(() => {
      const clientTime = Math.round(Date.now() / 1000);
      const startTime = game.startTime.seconds;
      const timePerQuestionAndAnswer = game.timePerQuestion + game.timePerAnswer;
      const whenThisQuestionStarted = startTime + game.currentQuestionIndex * timePerQuestionAndAnswer;
      const whenThisQuestionWillEnd = whenThisQuestionStarted + game.timePerQuestion;
      const timeRemaining = whenThisQuestionWillEnd - clientTime;
      if (timeRemaining < 0) {
        setTimer(0);
      } else {
        setTimer(timeRemaining);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [game.currentQuestionIndex])

  return (
    <>
      <input type="range" min="0" max={game.timePerQuestion} value={timer} readOnly />
    </>
  )
}
