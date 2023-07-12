import { useEffect, useState } from "react";
import { Game } from "../types";
import { DocumentReference } from "firebase/firestore";



const useTimer = ({ game, isAnswer, onTimeExpired }: { game: Game, isAnswer: Boolean, onTimeExpired: Function }) => {
  const [timer, setTimer] = useState<number>(isAnswer ? game.timePerAnswer : game.timePerQuestion);

  useEffect(() => {
    const interval = setInterval(() => {
      const clientTime = Math.round(Date.now() / 1000);
      const startTime = game.startTime.seconds;
      const timePerQuestionAndAnswer = game.timePerQuestion + game.timePerAnswer;
      const whenThisQuestionStarted = startTime + game.currentQuestionIndex * timePerQuestionAndAnswer;
      const whenThisQuestionWillEnd = whenThisQuestionStarted + game.timePerQuestion + (isAnswer ? game.timePerAnswer : 0 );
      const timeRemaining = whenThisQuestionWillEnd - clientTime;
      if (timeRemaining < 0) {
        onTimeExpired();
        setTimer(0);
      } else {
        setTimer(timeRemaining);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [game.startTime]);

  return { timer };
}

export default useTimer;