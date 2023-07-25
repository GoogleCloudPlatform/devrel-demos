"use client"

// Import the functions you need from the SDKs you need
import { db } from "@/app/lib/firebase-client-initialization";
import { onSnapshot, doc, DocumentReference } from "firebase/firestore";
import { useEffect, useState } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import CreateGameButton from "@/app/components/create-game-button";
import { Game, emptyGame, gameStates } from "@/app/types";
import GameList from "@/app/components/game-list";

export default function Home() {
  const [gameRef, setGameRef] = useState<DocumentReference>();
  const [game, setGame] = useState<Game>(emptyGame);
  const authUser = useFirebaseAuthentication();

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

  useEffect(() => {
    if (!authUser.uid) {
      setGameRef(undefined);
    }
  }, [authUser.uid])

  return (
    <div>
      {(game.state === gameStates.GAME_OVER) && <div>
        {gameStates.GAME_OVER}
      </div>}
      {(!gameRef || game.state === gameStates.GAME_OVER) && <div>
        <GameList />
        <CreateGameButton />
      </div>}
    </div>
  )
}
