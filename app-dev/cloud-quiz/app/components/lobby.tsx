"use client"

import { DocumentReference } from "firebase/firestore";
import StartGameButton from "./start-game-button";

export default function Lobby({gameRef}: {gameRef: DocumentReference}) {

  return (
    <StartGameButton gameRef={gameRef} />
  )
}
