"use client"

import { auth } from "@/app/lib/firebase-initialization";
import { DocumentReference, updateDoc } from "firebase/firestore";

export default function SubmitAnswerButton({gameRef, currentQuestionIndex, answerSelection}: {gameRef: DocumentReference, currentQuestionIndex: number, answerSelection: boolean[] }) {
  const onSubmitAnswerClick = async (gameRef: DocumentReference) => {
    if(!auth.currentUser) {
      throw new Error('Must have current user');
    } else {
      await updateDoc(gameRef, {
        [`questions.${currentQuestionIndex}.playerGuesses.${auth.currentUser.uid}`]: answerSelection,
      });
    };
  }

  return (
    <button onClick={() => onSubmitAnswerClick(gameRef)} className={`border mt-20`}>
      Submit Your Answer
    </button>
  )
}
