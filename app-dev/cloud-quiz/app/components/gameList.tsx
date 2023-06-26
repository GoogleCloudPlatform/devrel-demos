"use client"

import { Auth } from "firebase/auth";
import { DocumentReference, Firestore, collection, onSnapshot, query, updateDoc, where } from "firebase/firestore";
import { useEffect, useState } from "react";

export default function GameList({ auth, db, setGameRef }: { auth: Auth, db: Firestore, setGameRef: Function }) {
  const [gameList, setGameList] = useState();

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
      const games = [];
      querySnapshot.forEach((doc) => {
        games.push({ id: doc?.id, ref: doc?.ref });
      });
      setGameList(games);
    });
    return unsubscribe;
  }, [])

  return (
    <div>
      {gameList?.map(game => (
        <div key={game.id}>
          <button onClick={() => onJoinGameClick(game.ref)} className={`border mt-5`}>Join Game - {game.id}</button>
        </div>
      ))}
    </div>
  )
}
