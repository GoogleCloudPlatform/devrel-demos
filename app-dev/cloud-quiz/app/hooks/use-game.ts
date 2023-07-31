import { useEffect, useState } from "react";
import { auth, db } from "@/app/lib/firebase-client-initialization"
import { Game, emptyGame } from "@/app/types";
import { DocumentReference, doc, onSnapshot } from "firebase/firestore";


const useGame = (gameId: string) => {
  const [game, setGame] = useState<Game>(emptyGame);
  const [gameRef, setGameRef] = useState<DocumentReference>(doc(db, "games", gameId));
  const [error, setErrorMessage] = useState<string>("");

  useEffect(() => {
    const unsubscribe = onSnapshot(gameRef, (doc) => {
      const game = doc.data() as Game;
      if (game) {
        setGame(game);
        setGameRef(gameRef);
      } else {
        setErrorMessage(`Game ${gameId} was not found.`)
      }
    });
    return unsubscribe;
  }, [gameId])

  return { game, gameRef, error }
}

export default useGame;