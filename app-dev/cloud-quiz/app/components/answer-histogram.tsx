"use client"
import { signInAnonymously } from "firebase/auth";
import { onSnapshot, doc, DocumentReference, updateDoc } from "firebase/firestore";
import { db } from "@/app/lib/firebase-initialization";
import { Game, emptyGame, gameStates } from "@/app/types";
import { useEffect, useState } from 'react';


export default function AnswerHistogram() {
  const [gameRef, setGameRef] = useState<DocumentReference>();
  const [game, setGame] = useState<Game>(emptyGame);

  useEffect(() => {
    if (gameRef?.id) {
      const unsubscribe = onSnapshot(doc(db, "games", gameRef.id), (doc) => {
        const game = doc.data() as Game;
        setGame(game);
      });
      return unsubscribe;
    } else {
      setGame(emptyGame);
    }
  }, [gameRef])

  return (
    <pre>
      
        {JSON.stringify({
          game: {
            gameRefId: gameRef?.id,
            state: game.state,
            players: game.players,
            leader: game.leader,
          }
        }, null, 2)}
      </pre>
  )
}
