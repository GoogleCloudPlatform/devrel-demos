import { useEffect, useState } from "react";
import { db } from "@/app/lib/firebase-client-initialization"
import { Game, emptyGame, gameStates } from "@/app/types";
import { doc, onSnapshot } from "firebase/firestore";
import { usePathname } from "next/navigation";


const useGame = () => {
  const pathname = usePathname();
  const gameId = pathname.split('/')[2];
  const gameRef = doc(db, "games", gameId);
  const [game, setGame] = useState<Game>(emptyGame);
  const [error, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const unsubscribe = onSnapshot(gameRef, (doc) => {
      const game = doc.data() as Game;
      if (game) {
        setGame(game);
      } else {
        setErrorMessage(`Game ${gameId} was not found.`)
      }
    });
    return unsubscribe;
  }, [gameId, gameRef])

  return {
    gameRef,
    gameId,
    game,
    isShowingQuestion: game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS,
    currentQuestion: game.questions[game.currentQuestionIndex],
    error,
  }
}

export default useGame;