"use client"

import { Game } from "@/app/types";

export default function CountdownTimer({ game }: { game: Game }) {
  return (
    <>
      <input
        type="range"
        min="0"
        max={game.timePerQuestion}
        value={game.timeRemainingOnThisQuestion}
        readOnly
      />
    </>
  )
}
