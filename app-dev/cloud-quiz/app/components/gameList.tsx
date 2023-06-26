"use client"

import { db, auth } from "@/app/lib/firebase-initialization";
import { DocumentData, DocumentReference, collection, onSnapshot, query, updateDoc, where } from "firebase/firestore";
import { Dispatch, SetStateAction, useEffect, useState } from "react";

export default function GameList({ setGameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>> }) {
  const [gameList, setGameList] = useState<DocumentReference[]>();

  const onJoinGameClick = async (gameRef: DocumentReference) => {
    if (!auth.currentUser) throw new Error('User must be signed in to start game');

    updateDoc(gameRef, {
      [`players.${auth.currentUser.uid}`]: auth.currentUser.displayName,
    });

    setGameRef(gameRef);
  }

  useEffect(() => {
    const q = query(collection(db, "games"), where("state", "==", "NOT_STARTED"));
    const unsubscribe = onSnapshot(q, (querySnapshot) => {
      const games: DocumentReference[] = [];
      querySnapshot.forEach((doc) => {
        games.push(doc.ref);
      });
      setGameList(games);
    });
    return unsubscribe;
  }, [])

  return (
    <div>
      {gameList?.map(game => (
        <div key={game.id}>
          <button onClick={() => onJoinGameClick(game)} className={`border mt-5`}>Join Game - {game.id}</button>
        </div>
      ))}
    </div>
  )
}
