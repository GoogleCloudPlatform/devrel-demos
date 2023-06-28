"use client"

import { DocumentReference, updateDoc } from "firebase/firestore";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function SubmitAnswerButton({ gameRef, currentQuestionIndex, answerSelection }: { gameRef: DocumentReference, currentQuestionIndex: number, answerSelection: boolean[] }) {
  const authUser = useFirebaseAuthentication();

  const onSubmitAnswerClick = async (gameRef: DocumentReference) => {
    if (!authUser) throw new Error('Must have current user');

    await updateDoc(gameRef, {
      [`questions.${currentQuestionIndex}.playerGuesses.${authUser.uid}`]: answerSelection,
    });
  }

  return (
    <button onClick={() => onSubmitAnswerClick(gameRef)} className={`border mt-20 p-2 rounded-md`}>
      Submit Your Answer
    </button>
  )
}
