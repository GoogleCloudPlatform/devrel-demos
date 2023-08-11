"use client"

import GameList from "@/app/components/game-list";
import Navbar from "@/app/components/navbar";

export default function Home() {
  return (
    <div>
      <Navbar />
      <GameList />
      <br />
    </div>
  )
}
