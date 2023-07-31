"use client"

import CreateGameButton from "@/app/components/create-game-button";
import GameList from "@/app/components/game-list";

export default function Home() {
  return (
    <div>
      <GameList />
      <CreateGameButton />
    </div>
  )
}
