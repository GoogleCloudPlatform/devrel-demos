"use client"

import { db } from "@/app/lib/firebase-client-initialization";
import { DocumentReference, collection, onSnapshot, query, where } from "firebase/firestore";
import { useEffect, useState } from "react";
import { gameStates } from "../types";
import Link from "next/link";

export default function GameList() {
  const [gameList, setGameList] = useState<DocumentReference[]>();

  useEffect(() => {
    const q = query(collection(db, "games"), where("state", "!=", gameStates.GAME_OVER));
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
    <div className="p-2 mx-auto max-w-2xl">
      {(gameList && gameList.length > 0) ? gameList.map(game => (
        <div key={game.id} className={`border mt-5 p-2 rounded-md`}>
          <Link href={`/game/${game.id}`}>Join Game - {game.id}</Link>
        </div>
      )) : (<center className="mt-20">
        There are currently no games in progress.
      </center>)}
    </div>
  )
}
