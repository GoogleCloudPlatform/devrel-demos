"use client"

import Link from "next/link";
import useActiveGameList from "../hooks/use-active-game-list";

export default function GameList() {
  const {activeGameList} = useActiveGameList();

  return (
    <div className="p-2 mx-auto max-w-2xl">
      {activeGameList.length > 0 ? activeGameList.map(game => (
        <div key={game.id} className={`border mt-5 p-2 rounded-md`}>
          <Link href={`/game/${game.id}`}>Join Game - {game.id}</Link>
        </div>
      )) : (<center className="mt-20">
        There are currently no games in progress.
      </center>)}
    </div>
  )
}
