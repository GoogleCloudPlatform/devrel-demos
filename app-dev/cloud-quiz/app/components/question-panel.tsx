"use client"

import { DocumentReference } from "firebase/firestore";
import { Game, Question, gameStates } from "@/app/types";
import SubmitAnswerButton from "@/app/components/submit-answer-button";
import { useState, useEffect } from "react";
import CountdownTimer from "./countdown-timer";

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

  const currentQuestionIndex = game.currentQuestionIndex;

  return (
    <>
      <CountdownTimer game={game} />
      <h2 className="text-2xl font-light">
        {currentQuestion.prompt}
      </h2>
      <hr className="w-100 my-4"></hr>
      <div className="grid grid-cols-2">
        {currentQuestion.answers.map((answer, index) => (<div className="flex pt-2 	aspect-square" key={answer.text}>
          {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
            <div>
              {answer.isCorrect && '✅'}
              {!answer.isCorrect && answerSelection[index] && '❌'}
            </div>)}
          <button onClick={() => onAnswerClick(index)}
            className=
            {`border-8 m-8 aspect-square
                ${answerSelection[index] ? 'text-blue-500' : 'text-inherit'}
                ${answerSelection[index] && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-green-500'}
                ${answerSelection[index] && !answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-red-500'}
                ${!answerSelection[index] && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-green-500 border-dotted'} `}>
            {answer.text}
          </button>
        </div>))}
      </div>
      {game.state === gameStates.AWAITING_PLAYER_ANSWERS && (<>
        {answerSelection.some(selection => selection === true) ? (<>
          <SubmitAnswerButton gameRef={gameRef} currentQuestionIndex={currentQuestionIndex} answerSelection={answerSelection} />
        </>) : (<>
          <div className={`mt-20 text-gray-500`}>
            Select an Answer
          </div>
        </>)}
      </>)}
      {/* {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
        <button onClick={() => onNextQuestionClick({game, gameRef})} className={`border mt-20 p-2 rounded-md`}>
          Next Question ({timer})
        </button>
      )} */}
    </>
  )
}
