"use client"

import { DocumentReference, updateDoc } from "firebase/firestore";
import { Game, Question, gameStates } from "@/app/types";
import RevealAnswersButton from "@/app/components/reveal-answers-button";
import SubmitAnswerButton from "@/app/components/submit-answer-button";
import { useState, useEffect } from "react";

export default function QuestionPanel({ game, gameRef, currentQuestion }: { game: Game, gameRef: DocumentReference, currentQuestion: Question }) {
  const [answerSelection, setAnswerSelection] = useState<boolean[]>([]);

  const onAnswerClick = (answerIndex: number): void => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
      // typescript gives an error for `.with` because it is a newer property
      // this can likely be removed once typescript is updated
      // @ts-expect-error
      setAnswerSelection(answerSelection.with(answerIndex, !answerSelection[answerIndex]));
    }
  }

  useEffect(() => {
    if (currentQuestion?.answers.length) {
      setAnswerSelection(Array(currentQuestion.answers.length).fill(false));
    }
  }, [game.currentQuestionIndex])

  const onNextQuestionClick = async () => {
    if (gameRef?.id) {
      if (game.currentQuestionIndex < Object.keys(game.questions).length - 1) {
        await updateDoc(gameRef, {
          currentQuestionIndex: game.currentQuestionIndex + 1,
          state: gameStates.AWAITING_PLAYER_ANSWERS,
        });
      } else {
        await updateDoc(gameRef, {
          state: gameStates.GAME_OVER,
        });
      }
    }
  }

  const currentQuestionIndex = game.currentQuestionIndex;

  return (
    <>
      <h2>
        {currentQuestion.prompt}
      </h2>
      {currentQuestion.answers.map((answer, index) => (<div className="flex pt-2" key={answer.text}>
        {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
          <div>
            {answer.isCorrect && '✅'}
            {!answer.isCorrect && answerSelection[index] && '❌'}
          </div>)}
        <button onClick={() => onAnswerClick(index)} className={`border ${answerSelection[index] ? 'text-blue-500' : 'text-inherit'}`}>
          {answer.text}
        </button>
      </div>))}
      {game.state === gameStates.AWAITING_PLAYER_ANSWERS && (<>
        {answerSelection.some(selection => selection === true) ? (<>
          <SubmitAnswerButton gameRef={gameRef} currentQuestionIndex={currentQuestionIndex} answerSelection={answerSelection} />
        </>) : (<>
          <div className={`mt-20 text-gray-500`}>
            Select an Answer
          </div>
        </>)}
        <RevealAnswersButton gameRef={gameRef} />
      </>)}
      {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
        <button onClick={onNextQuestionClick} className={`border mt-20`}>
          Next Question
        </button>
      )}
    </>
  )
}
