"use client"

import { DocumentReference } from "firebase/firestore";
import { Game, Question, gameStates } from "@/app/types";
import BorderCountdownTimer from "@/app/components/border-countdown-timer";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function QuestionPanel({ game, gameRef, currentQuestion }: { game: Game, gameRef: DocumentReference, currentQuestion: Question }) {
  const authUser = useFirebaseAuthentication();

  const existingGuesses = currentQuestion?.playerGuesses && currentQuestion.playerGuesses[authUser.uid];
  const answerSelection = existingGuesses || Array(currentQuestion.answers.length).fill(false);

  const onAnswerClick = async (answerIndex: number) => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
      const newAnswerSelection = answerSelection.with(answerIndex, !answerSelection[answerIndex]);
      const token = await authUser.getIdToken();
      await fetch('/api/update-answer', {
        method: 'POST',
        body: JSON.stringify({ newAnswerSelection, gameId: gameRef.id }),
        headers: {
          Authorization: token,
        }
      })
        .catch(error => {
          console.error({ error })
        });
    }
  }


  return (
    <div className="grid lg:grid-cols-2">
      <BorderCountdownTimer game={game}>
        <h2 className="text-2xl font-light">
          {currentQuestion.prompt}
        </h2>
      </BorderCountdownTimer>
      <div className="grid grid-cols-2">
        {currentQuestion.answers.map((answer, index) => (<div className="flex py-2 	aspect-square" key={answer.text}>
          <button onClick={() => onAnswerClick(index)}
            className=
            {`border-8 m-2 aspect-square
                ${answerSelection[index] ? 'text-[var(--google-cloud-blue)]' : 'text-inherit'}
                ${answerSelection[index] && game.state !== gameStates.SHOWING_CORRECT_ANSWERS ? 'border-[var(--google-cloud-blue)]' : ''}
                ${answerSelection[index] && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-[var(--google-cloud-green)]'}
                ${answerSelection[index] && !answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-[var(--google-cloud-red)]'}
                ${!answerSelection[index] && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-[var(--google-cloud-green)] border-dotted'}`}>
            {answer.text}
            {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
              <div>
                {answer.isCorrect && '✅'}
                {!answer.isCorrect && answerSelection[index] && '❌'}
              </div>)}
          </button>
        </div>))}
      </div>
    </div>
  )
}
