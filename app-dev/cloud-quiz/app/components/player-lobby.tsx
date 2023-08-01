"use client"

import { DocumentReference } from "firebase/firestore";
import ExitGameButton from "@/app/components/exit-game-button";
import PlayerList from "./player-list";
import { Game } from "@/app/types";

export default function PlayerLobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {
  return (
    <>
      <ExitGameButton gameRef={gameRef} />
      <PlayerList game={game} />
    </>
  )
}
