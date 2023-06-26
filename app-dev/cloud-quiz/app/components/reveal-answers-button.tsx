"use client"

import { DocumentReference, updateDoc } from "firebase/firestore";
import { gameStates } from "@/app/types";

export default function RevealAnswersButton({gameRef}: {gameRef: DocumentReference}) {
  const onRevealAnswersClick = async (gameRef: DocumentReference) => {
    await updateDoc(gameRef, {
      state: gameStates.SHOWING_CORRECT_ANSWERS,
    });
  }

  return (
    <button onClick={() => onRevealAnswersClick(gameRef)} className={`border mt-20`}>
      Reveal Answers
    </button>
  )
}
