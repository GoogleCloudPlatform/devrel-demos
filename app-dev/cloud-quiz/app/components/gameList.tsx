"use client"

import { db } from "@/app/lib/firebase-initialization";
import { DocumentData, DocumentReference, collection, onSnapshot, query, updateDoc, where } from "firebase/firestore";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function GameList({ setGameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>> }) {
  const [gameList, setGameList] = useState<DocumentReference[]>();
  const authUser = useFirebaseAuthentication();

  const onJoinGameClick = async (gameRef: DocumentReference) => {
    if (!authUser) throw new Error('User must be signed in to start game');

    updateDoc(gameRef, {
      [`players.${authUser.uid}`]: authUser.displayName,
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
