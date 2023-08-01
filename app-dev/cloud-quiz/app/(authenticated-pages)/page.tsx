"use client"

import CreateGameButton from "@/app/components/create-game-button";
import GameList from "@/app/components/game-list";
import SignOutButton from "@/app/components/sign-out-button";

export default function Home() {
  return (
    <div>
      <GameList />
      <CreateGameButton />
      <br />
      <SignOutButton />
    </div>
  )
}
