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

'use client';

import {DocumentReference} from 'firebase/firestore';
import {Game, Question, gameStates} from '@/app/types';
import BorderCountdownTimer from '@/app/components/border-countdown-timer';
import useFirebaseAuthentication from '@/app/hooks/use-firebase-authentication';
import Image from 'next/image';
import QRCode from 'react-qr-code';
import {useEffect, useState} from 'react';
import Scoreboard from './scoreboard';
import useScoreboard from '../hooks/use-scoreboard';

export default function QuestionPanel({game, gameRef, currentQuestion}: { game: Game, gameRef: DocumentReference, currentQuestion: Question }) {
  const authUser = useFirebaseAuthentication();
  const {currentPlayer, playerScores} = useScoreboard();
  const isGameLeader = authUser.uid === game.leader.uid;
  const [answersSelectedCount, setAnswersSelectedCount] = useState<number>(0);

  const existingGuesses = currentQuestion?.playerGuesses && currentQuestion.playerGuesses[authUser.uid];
  const emptyAnswerSelection = Array(currentQuestion.answers.length).fill(false);
  const answerSelection = existingGuesses || emptyAnswerSelection;

  const totalCorrectAnswerOptions = currentQuestion.answers.reduce((correctAnswerCount, answer) => {
    return correctAnswerCount + (answer.isCorrect ? 1 : 0);
  }, 0);

  useEffect(() => {
    setAnswersSelectedCount(answerSelection.reduce((correctAnswerCount, answerIsSelected) => {
      return correctAnswerCount + (answerIsSelected ? 1 : 0);
    }, 0));
  }, [answerSelection]);

  const isSingleAnswer = totalCorrectAnswerOptions === 1;

  const onAnswerClick = async (answerIndex: number) => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS && !isGameLeader) {
      // If the user is only supposed to pick one answer, clear the other answers first
      const startingAnswerSelection = isSingleAnswer ? emptyAnswerSelection : answerSelection;

      // Typescript does not expect the `with` property on arrays yet
      // @ts-expect-error
      const newAnswerSelection: Boolean[] = startingAnswerSelection.with(answerIndex, !answerSelection[answerIndex]);

      const token = await authUser.getIdToken();
      await fetch('/api/update-answer', {
        method: 'POST',
        body: JSON.stringify({answerSelection: newAnswerSelection, gameId: gameRef.id}),
        headers: {
          Authorization: token,
        },
      }).catch((error) => {
        console.error({error});
      });
    }
  };

  const gameShareLink = `${location.protocol}//${location.host}/game/${gameRef.id}`;

  const isShowingCorrectAnswers = game.state === gameStates.SHOWING_CORRECT_ANSWERS;

  const totalPlayersWhoMadeAGuess = Object.values(currentQuestion.playerGuesses || []).length;

  const countLeftToPick = totalCorrectAnswerOptions - answersSelectedCount;

  return (
    <div className={`grid lg:grid-cols-2`}>
      <div className="flex flex-col">
        <BorderCountdownTimer game={game} gameRef={gameRef}>
          <div className="flex flex-col justify-between h-full">
            <h2 className={isShowingCorrectAnswers ? 'transition-all text-sm font-light' : 'text-lg md:text-2xl lg:text-4xl'}>
              {currentQuestion.prompt}
            </h2>
            {isShowingCorrectAnswers ? (<>
              <h2 className="md:text-xl lg:text-2xl pt-5">
                {currentQuestion.explanation}
              </h2>
            </>) : (<div>
              <h2 className="text-xl lg:text-4xl pt-5">
                Pick {totalCorrectAnswerOptions}
              </h2>
              {!isGameLeader && (
                <h3 className="font-light text-lg lg:text-xl">
                  {countLeftToPick !== 0 ? (
                    `Pick ${Math.abs(countLeftToPick)} ${countLeftToPick > 0 ? 'More' : 'Less'}`
                  ) : 'You are all set'}
                </h3>
              )}
            </div>)}
          </div>
        </BorderCountdownTimer>
        <center className='hidden bg-gray-100 h-[50dvh] lg:block overflow-hidden'>
          {currentPlayer.displayName && <div className="mt-2">You are {currentPlayer.displayName}</div>}
          {isShowingCorrectAnswers && currentPlayer?.score > -1 && <div>and you have {currentPlayer.score} point{currentPlayer.score === 1 ? '' : 's'}</div>}
          {(isShowingCorrectAnswers && playerScores.length > 0) ? (<>
            <Scoreboard />
          </>) : (<>
            {isGameLeader ? (<div className="flex h-full">
              <div className="m-auto">
                <div>
                  Just getting here?
                </div>
                <div>
                  Scan the QR Code to join the game!
                </div>
                <QRCode value={gameShareLink} />
              </div>
            </div>) : (<>
              <center className='pt-20'>
                <div className='h-20'>
                  <Image
                    src='/google-cloud-logo.svg'
                    alt='Google Cloud Logo'
                    width={0}
                    height={0}
                    sizes="100vw"
                    style={{width: '100%', height: '100%'}} // optional
                    priority
                  />
                </div>
                <h1 className='text-4xl pt-10'>Party Game</h1>
              </center>
            </>)}
          </>)}
        </center>
      </div>
      <div className="grid grid-rows-4 h-[50dvh] lg:h-full">
        {currentQuestion.answers.map((answer, index) => {
          const guessesForThisAnswer = Object.values(currentQuestion.playerGuesses || []).reduce((playerGuesses, guess) => {
            return playerGuesses + (guess[index] ? 1 : 0);
          }, 0);

          const guessPercentageForThisAnswer = guessesForThisAnswer / (totalPlayersWhoMadeAGuess || 1) * 100;
          const colorOrder = ['red', 'blue', 'green', 'yellow'];
          const color = colorOrder[index];
          const isSelected = answerSelection[index];

          return (<div className="flex" key={answer.text}>
            <button
              onClick={() => onAnswerClick(index)}
              className="m-1 w-full relative flex content-start text-left overflow-hidden"
            >
              <div className="w-full px-1 m-auto line-clamp-1 overflow-hidden border-8 border-transparent flex justify-between h-fit">
                <span className={`h-fit text-xl lg:text-3xl my-auto`}>
                  {isSingleAnswer && (isSelected ? '●' : '○')}
                  {!isSingleAnswer && (isSelected ? '☑' : '☐')}
                  {answer.text}
                </span>
              </div>
              {isShowingCorrectAnswers && (<>
                <div className="absolute bottom-0 right-0 border-8 border-transparent min-w-fit h-full text-right text-lg lg:text-2xl flex">
                  <div className="h-full w-20 max-w-full bg-gradient-to-l from-white via-transparent via-white via-20% -m-1" />
                  <div className="bg-white pl-1 h-fit my-auto">
                    <div className="whitespace-nowrap">
                      {answer.isCorrect && isSelected && 'You got it '}
                      {answer.isCorrect && !isSelected && !isGameLeader && 'You missed this one '}
                      {answer.isCorrect && ' ✭'}
                      {!answer.isCorrect && (isSelected ? 'Not this one ✖' : <div className="whitespace-wrap">&nbsp;</div>)}
                    </div>
                    <div>
                      {guessesForThisAnswer} / {totalPlayersWhoMadeAGuess}
                    </div>
                  </div>
                </div>
              </>)
              }
              <div className="absolute bottom-0 h-full w-full text-black">
                <div
                  className={`absolute bottom-0 left-0 h-full opacity-25 transition-all duration-[3000ms]`}
                  style={{
                    backgroundColor: answer.isCorrect ? `var(--google-cloud-${color})` : '#9ca3af',
                    width: `${isShowingCorrectAnswers ? Math.max(guessPercentageForThisAnswer, 2) : 0}%`,
                  }}
                />
              </div>
              <div
                className={`transition-all ${isSelected ? 'border-8' : 'border-4'} w-full absolute bottom-0 h-full`}
                style={{
                  borderColor: `var(--google-cloud-${color})`,
                }}
              />
            </button>
          </div>);
        })}
      </div >
    </div >
  );
}
