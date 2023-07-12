"use client"

import { DocumentReference, updateDoc } from "firebase/firestore";
import { Game, gameStates } from "@/app/types";
import useTimer from "@/app/hooks/use-timer";

export default function RevealAnswersButton({game, gameRef}: {game: Game, gameRef: DocumentReference}) {

  const onRevealAnswersClick = async (gameRef: DocumentReference) => {
    await updateDoc(gameRef, {
      state: gameStates.SHOWING_CORRECT_ANSWERS,
    });
  }
  const { timer } = useTimer({ game, isAnswer: false, onTimeExpired: () => onRevealAnswersClick(gameRef) });

  return (
    <button onClick={() => onRevealAnswersClick(gameRef)} className={`border mt-20 p-2 rounded-md`}>
      Reveal Answers ({timer})
    </button>
  )
}
