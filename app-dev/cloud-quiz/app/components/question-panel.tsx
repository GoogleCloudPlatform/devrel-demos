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
  const answerSelection = existingGuesses || Array(currentQuestion.answers.length).fill(false);

  const onAnswerClick = async (answerIndex: number) => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
      // Typescript does not expect the `with` property on arrays yet
      // @ts-expect-error
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

  const gameShareLink = `${location.protocol}//${location.host}/game/${gameRef.id}`;

  const answerBorder = ({ isSelected, answer, game }: { isSelected: Boolean, answer: Answer, game: Game }): string => {
    return mergeClassNames(
      "border-8 m-2 w-full",
      isSelected ? 'text-[var(--google-cloud-blue)]' : 'text-inherit',
      isSelected && game.state !== gameStates.SHOWING_CORRECT_ANSWERS ? 'border-[var(--google-cloud-blue)]' : '',
      isSelected && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS ? 'border-[var(--google-cloud-green)]' : '',
      isSelected && !answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS ? 'border-[var(--google-cloud-red)]' : '',
      !isSelected && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS ? 'border-[var(--google-cloud-green)] border-dotted' : '',
    );
  }

  return (
    <div className={`grid lg:grid-cols-2`}>
      <div className="flex flex-col">
        <BorderCountdownTimer game={game} gameRef={gameRef}>
          <h2 className="text-lg lg:text-2xl">
            {currentQuestion.prompt}
          </h2>
          {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (<>
            <h2 className="text-sm lg:text-xl font-light pt-5">
              {currentQuestion.explanation}
            </h2>
          </>)}
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
      <div className="grid grid-cols-2 h-[50vh] lg:h-full">
        {currentQuestion.answers.map((answer, index) => (<div className="flex" key={answer.text}>
          <button
            onClick={() => onAnswerClick(index)}
            className={answerBorder({ isSelected: answerSelection[index], game, answer })}
          >
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
