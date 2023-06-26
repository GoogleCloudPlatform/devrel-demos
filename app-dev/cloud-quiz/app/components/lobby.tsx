"use client"

import { DocumentReference } from "firebase/firestore";
import StartGameButton from "./start-game-button";
import ExitGameButton from "./exitGameButton";

export default function Lobby({ gameRef, setGameRef }: { gameRef: DocumentReference, setGameRef: Function }) {

  return (
    <>
      <StartGameButton gameRef={gameRef} />
      <ExitGameButton setGameRef={setGameRef} />
    </>
  )
}
