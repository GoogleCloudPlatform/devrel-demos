"use client"

import { DocumentReference } from "firebase/firestore";
import StartGameButton from "@/app/components/start-game-button";
import ExitGameButton from "@/app/components/exitGameButton";

export default function Lobby({ gameRef, setGameRef }: { gameRef: DocumentReference, setGameRef: Function }) {

  return (
    <>
      <StartGameButton gameRef={gameRef} />
      <ExitGameButton setGameRef={setGameRef} gameRef={gameRef} />
    </>
  )
}
