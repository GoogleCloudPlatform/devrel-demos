"use client"

import { DocumentReference } from "firebase/firestore";
import StartGameButton from "./start-game-button";
import ExitGameButton from "./exitGameButton";
import { Auth } from "firebase/auth";

export default function Lobby({ auth, gameRef, setGameRef }: { auth: Auth, gameRef: DocumentReference, setGameRef: Function }) {

  return (
    <>
      <StartGameButton gameRef={gameRef} />
      <ExitGameButton auth={auth} setGameRef={setGameRef} gameRef={gameRef} />
    </>
  )
}
