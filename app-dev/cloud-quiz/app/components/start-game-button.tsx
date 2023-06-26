"use client"

import { DocumentReference, updateDoc } from "firebase/firestore";
import { gameStates } from "@/app/types";

export default function StartGameButton({gameRef}: {gameRef: DocumentReference}) {
  const onStartGameClick = async (gameRef: DocumentReference) => {
    await updateDoc(gameRef, {
      state: gameStates.AWAITING_PLAYER_ANSWERS,
    });
  }

  return (
    <button onClick={() => onStartGameClick(gameRef)} className={`border mt-20`}>
      Start Game
    </button>
  )
}
