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

import {Game, GameStateUpdate, gameStates, questionAdvancements} from '@/app/types';
import {DocumentReference, Timestamp} from 'firebase/firestore';
import {useEffect, useState, useCallback} from 'react';
import useFirebaseAuthentication from '@/app/hooks/use-firebase-authentication';
import {nudgeGameAction} from '@/app/actions/nudge-game';
import {getTokens} from '@/app/lib/client-token-generator';

const {MANUAL} = questionAdvancements;

export default function BorderCountdownTimer({game, children, gameRef}: { game: Game, children: React.ReactNode, gameRef: DocumentReference }) {
  const [timeLeft, setTimeLeft] = useState<number>(game.timePerQuestion);
  const [localCounter, setLocalCounter] = useState<number>(0);
  const gameId = gameRef.id;
  const authUser = useFirebaseAuthentication();
  const isShowingCorrectAnswers = game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const displayTime = MANUAL === game.questionAdvancement && isShowingCorrectAnswers ? 0 : Math.max(Math.floor(timeLeft), 0);
  const timeToCountDown = isShowingCorrectAnswers ? game.timePerAnswer : game.timePerQuestion;
  const totalPlayersWhoMadeAGuess = Object.values(game.questions[game.currentQuestionIndex].playerGuesses || []).length;

  const nudgeGame = useCallback(async ({gameId, desiredState}: { gameId: string, desiredState: GameStateUpdate }) => {
    if (game.state === desiredState.state && game.currentQuestionIndex === desiredState.currentQuestionIndex) return;
    // all times are in seconds unless noted as `InMillis`
    const timeElapsedInMillis = Timestamp.now().toMillis() - game.currentStateStartTime.seconds * 1000;
    const timeElapsed = timeElapsedInMillis / 1000;
    if (authUser.uid === game.leader.uid && timeElapsed > 2) {
      const tokens = await getTokens();
      nudgeGameAction({gameId, desiredState, tokens});
    }
  }, [authUser.uid, game.currentQuestionIndex, game.currentStateStartTime.seconds, game.leader.uid, game.state]);

  useEffect(() => {
    // all times are in seconds unless noted as `InMillis`
    const timeElapsedInMillis = Timestamp.now().toMillis() - game.currentStateStartTime.seconds * 1000;
    const timeElapsed = timeElapsedInMillis / 1000;
    const isShowingCorrectAnswers = game.state === gameStates.SHOWING_CORRECT_ANSWERS;

    if (isShowingCorrectAnswers) {
      const timeLeft = game.timePerAnswer - timeElapsed;
      if (timeLeft < 0 && game.questionAdvancement === questionAdvancements.AUTOMATIC) {
        const desiredState = {
          state: gameStates.AWAITING_PLAYER_ANSWERS,
          currentQuestionIndex: game.currentQuestionIndex + 1,
        };
        nudgeGame({gameId, desiredState});
      }
      setTimeLeft(timeLeft);
    } else {
      const timeLeft = game.timePerQuestion - timeElapsed;
      if (timeLeft < 0) {
        const desiredState = {
          state: gameStates.SHOWING_CORRECT_ANSWERS,
          currentQuestionIndex: game.currentQuestionIndex,
        };
        nudgeGame({gameId, desiredState});
      }
      setTimeLeft(timeLeft);
    }
  }, [localCounter, game.currentStateStartTime, game.currentQuestionIndex, game.timePerAnswer, game.timePerQuestion, isShowingCorrectAnswers, game.state, game.leader.uid, game.questionAdvancement, authUser.uid, gameId, nudgeGame]);

  useEffect(() => {
    // save timeoutIdOne to clear the timeout when the
    // component re-renders
    const timeoutIdOne = setTimeout(() => {
      setLocalCounter(localCounter + 1);
    }, 1000);

    // clear timeout on re-render to avoid memory leaks
    return () => clearTimeout(timeoutIdOne);
  }, [localCounter, game.state]);

  const limitPercents = (num: number) => Math.max(Math.min(num, 100), 0);

  // this is the percent of the entire animation that has completed
  // the `+ 1` allows the animation to target where it "should" be in one second
  const timeToCountDivisibleByFour = Math.floor(timeToCountDown / 4) * 4;
  const animationCompletionPercentage = limitPercents((timeToCountDivisibleByFour - displayTime + 1) / timeToCountDivisibleByFour * 100);

  const topBorderPercentage = limitPercents(isShowingCorrectAnswers ? 400 - animationCompletionPercentage * 4 : animationCompletionPercentage * 4);
  const rightBorderPercentage = limitPercents(isShowingCorrectAnswers ? 300 - animationCompletionPercentage * 4 : animationCompletionPercentage * 4 - 100);
  const bottomBorderPercentage = limitPercents(isShowingCorrectAnswers ? 200 - animationCompletionPercentage * 4 : animationCompletionPercentage * 4 - 200);
  const leftBorderPercentage = limitPercents(isShowingCorrectAnswers ? 100 - animationCompletionPercentage * 4 : animationCompletionPercentage * 4 - 300);


  return (
    <>
      <div className={`relative p-4 h-[50dvh] overflow-hidden`}>
        <div className="absolute border-2 border-gray-100 h-full w-full top-0 left-0" />
        <div className="timer-top-border absolute top-0 left-0 bg-[var(--google-cloud-red)]" style={{height: '8px', width: `${topBorderPercentage}%`, transition: 'width 1s linear'}} />
        <div className="timer-right-border absolute top-0 right-0 bg-[var(--google-cloud-blue)]" style={{height: `${rightBorderPercentage}%`, width: '8px', transition: 'height 1s linear'}} />
        <div className="timer-bottom-border absolute bottom-0 right-0 bg-[var(--google-cloud-green)]" style={{height: '8px', width: `${bottomBorderPercentage}%`, transition: 'width 1s linear'}} />
        <div className="timer-left-border absolute bottom-0 left-0 bg-[var(--google-cloud-yellow)]" style={{height: `${leftBorderPercentage}%`, width: '8px', transition: 'height 1s linear'}} />
        <div className="h-full w-full border-8 border-transparent">
          <div className="bg-gray-100 py-1 px-2 float-right relative">
            {displayTime < 10 && '0'}
            {displayTime}
            {authUser.uid === game.leader.uid && (<>
              <div>
                {totalPlayersWhoMadeAGuess < 10 && '0'}
                {totalPlayersWhoMadeAGuess}
              </div>
              <div>&nbsp;</div>
              <div className="my-1 absolute bottom-0">
                <button
                  onClick={() => {
                    const desiredState = {
                      state: isShowingCorrectAnswers ? gameStates.AWAITING_PLAYER_ANSWERS : gameStates.SHOWING_CORRECT_ANSWERS,
                      currentQuestionIndex: isShowingCorrectAnswers ? game.currentQuestionIndex + 1 : game.currentQuestionIndex,
                    };
                    console.log('clicked');
                    nudgeGame({gameId, desiredState});
                  }}
                >
                  {'→'}
                </button>
              </div>
            </>)}
          </div>
          {children}
        </div>
      </div>
    </>
  );
}
