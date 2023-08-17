/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

"use client"

import { DocumentReference } from "firebase/firestore";
import { Answer, Game, Question, gameStates } from "@/app/types";
import BorderCountdownTimer from "@/app/components/border-countdown-timer";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import Image from 'next/image';
import QRCode from "react-qr-code";
import { usePathname } from "next/navigation";
import { mergeClassNames } from "../lib/merge-class-names";

export default function QuestionPanel({ game, gameRef, currentQuestion }: { game: Game, gameRef: DocumentReference, currentQuestion: Question }) {
  const authUser = useFirebaseAuthentication();
  const pathname = usePathname();
  const isPresenter = pathname.includes('/presenter');

  const existingGuesses = currentQuestion?.playerGuesses && currentQuestion.playerGuesses[authUser.uid];
  const emptyAnswerSelection = Array(currentQuestion.answers.length).fill(false);
  const answerSelection = existingGuesses || emptyAnswerSelection;

  const totalCorrectAnswerOptions = currentQuestion.answers.reduce((correctAnswerCount, answer) => {
    return correctAnswerCount + (answer.isCorrect ? 1 : 0);
  }, 0);

  const onAnswerClick = async (answerIndex: number) => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
      // If the user is only supposed to pick one answer, clear the other answers first
      const startingAnswerSelection = totalCorrectAnswerOptions === 1 ? emptyAnswerSelection : answerSelection;

      // Typescript does not expect the `with` property on arrays yet
      // @ts-expect-error
      const newAnswerSelection = startingAnswerSelection.with(answerIndex, !answerSelection[answerIndex]);
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

  const gameShareLink = `${location.protocol}//${location.host}/game/${gameRef.id}`;

  const isShowingCorrectAnswers = game.state === gameStates.SHOWING_CORRECT_ANSWERS;

  const totalPlayerGuesses = Object.values(currentQuestion.playerGuesses || []).length;

  return (
    <div className={`grid lg:grid-cols-2`}>
      <div className="flex flex-col">
        <BorderCountdownTimer game={game} gameRef={gameRef}>
          <h2 className={isShowingCorrectAnswers ? 'text-sm' : 'text-lg md:text-2xl lg:text-4xl'}>
            {currentQuestion.prompt}
          </h2>
          <h2 className="lg:text-xl pt-5">
            {isShowingCorrectAnswers ? currentQuestion.explanation : (<>[Pick {totalCorrectAnswerOptions}]</>)}
          </h2>
        </BorderCountdownTimer>
        <center className='hidden bg-gray-100 p-10 h-[50vh] lg:block'>
          {isPresenter ? (<>
            <div>
              Just getting here?
            </div>
            <div>
              Scan the QR Code to join the game!
            </div>
            <QRCode value={gameShareLink} />
          </>) : (<>
            <center className='pt-20'>
              <div className='h-20'>
                <Image
                  src='/google-cloud-logo.svg'
                  alt='Google Cloud Logo'
                  width={0}
                  height={0}
                  sizes="100vw"
                  style={{ width: '100%', height: '100%' }} // optional
                  priority
                />
              </div>
              <h1 className='text-4xl pt-10'>Party Game</h1>
            </center>
          </>)}
        </center>
      </div>
      <div className="grid grid-rows-4 h-[50vh] lg:h-full">
        {currentQuestion.answers.map((answer, index) => {
          const guessesForThisAnswer = Object.values(currentQuestion.playerGuesses || []).reduce((playerGuesses, guess) => {
            return playerGuesses + (guess[index] ? 1 : 0);
          }, 0);

          const guessPercentageForThisAnswer = guessesForThisAnswer / (totalPlayerGuesses || 1) * 100;
          const colorOrder = ['red', 'blue', 'green', 'yellow'];
          const color = colorOrder[index];
          const isSelected = answerSelection[index];

          return (<div className="flex" key={answer.text}>
            <button
              onClick={() => onAnswerClick(index)}
              className="m-2 w-full relative flex content-start text-left overflow-hidden"
            >
              <div className="w-full px-1 m-auto line-clamp-1 overflow-hidden border-8 border-transparent flex justify-between h-fit">
                <span className="h-fit text-xl lg:text-3xl my-auto">
                  {answer.text}
                </span>
                {isShowingCorrectAnswers && (<>
                  <span className="min-w-fit h-fit my-auto text-right text-lg lg:text-2xl">
                    <div>
                      {answer.isCorrect && isSelected && 'You got it '}
                      {answer.isCorrect && !isSelected && !isPresenter && 'You missed this one '}
                      {answer.isCorrect && ' ✓'}
                      {!answer.isCorrect && (isSelected ? 'Not this one ✖' : <>&nbsp;</>)}
                    </div>
                    <div>
                      {guessesForThisAnswer} / {totalPlayerGuesses}
                    </div>
                  </span>
                </>)}
              </div>

              <div
                className={`transition-all ${isSelected ? 'border-8' : 'border-4'} w-full absolute bottom-0 h-full`}
                style={{
                  borderColor: `var(--google-cloud-${color})`,
                }}
              />
              {isShowingCorrectAnswers && (<>
                <div className="absolute bottom-0 h-full w-full text-black -z-50">
                  <div
                    className={`absolute bottom-0 left-0 h-full opacity-25`}
                    style={{
                      backgroundColor: answer.isCorrect ? `var(--google-cloud-${color})` : '#e5e7eb',
                      width: `${Math.min(Math.max(guessPercentageForThisAnswer, 2))}%`
                    }}
                  />
                </div>
              </>)
              }
            </button>
          </div>)
        })}
      </div >
    </div >
  )
}
