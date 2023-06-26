"use client"

import { DocumentData, DocumentReference } from "firebase/firestore";
import StartGameButton from "@/app/components/start-game-button";
import ExitGameButton from "@/app/components/exitGameButton";
import { Dispatch, SetStateAction } from "react";

export default function Lobby({ gameRef, setGameRef }: { gameRef: DocumentReference, setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>> }) {

  return (
    <>
      <StartGameButton gameRef={gameRef} />
      <ExitGameButton setGameRef={setGameRef} gameRef={gameRef} />
    </>
  )
}
