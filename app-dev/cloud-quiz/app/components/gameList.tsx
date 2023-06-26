"use client"

import { Firestore, collection, onSnapshot, query, where } from "firebase/firestore";
import { useEffect, useState } from "react";

export default function GameList({ db, setGameRef }: { db: Firestore, setGameRef: Function }) {
  const [gameList, setGameList] = useState();

  useEffect(() => {
    const q = query(collection(db, "games"), where("state", "==", "NOT_STARTED"));
    const unsubscribe = onSnapshot(q, (querySnapshot) => {
      const games = [];
      querySnapshot.forEach((doc) => {
        games.push({id: doc?.id, ref: doc?.ref });
      });
      setGameList(games);
      console.log({ games });
    });
    return unsubscribe;
  }, [])

  return (
    <div>
      {gameList?.map(game => (
        <button onClick={() => setGameRef(game.ref)} className={`border mt-20`}>Join Game - {game.id}</button>
      ))}
    </div>
  )
}
