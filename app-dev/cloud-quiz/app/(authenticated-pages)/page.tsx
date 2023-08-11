"use client"

import useActiveGameList from "@/app/hooks/use-active-game-list";
import { useRouter } from 'next/navigation'
import Navbar from "@/app/components/navbar";

export default function Home() {
  const { activeGameList } = useActiveGameList();
  const router = useRouter()

  if (activeGameList.length > 0) {
    const firstGameId = activeGameList[0].id;
    router.push(`/game/${firstGameId}`);
  }

  return (
    <div>
      <Navbar />
      <center className="p-8">
        Waiting for a game.
      </center>
    </div>
  )
}
