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

import {Game, gameStates} from '@/app/types';
import {DocumentReference, Timestamp} from 'firebase/firestore';
import {useEffect, useState} from 'react';
import useFirebaseAuthentication from '@/app/hooks/use-firebase-authentication';
import {nudgeGameAction} from '@/app/actions/nudge-game';
import {getTokens} from '@/app/lib/client-token-generator';

export default function BorderCountdownTimer({game, children, gameRef}: { game: Game, children: React.ReactNode, gameRef: DocumentReference }) {
  const [timeLeft, setTimeLeft] = useState<number>(game.timePerQuestion);
  const displayTime = Math.max(Math.floor(timeLeft), 0);
  const [localCounter, setLocalCounter] = useState<number>(0);
  const gameId = gameRef.id;
  const authUser = useFirebaseAuthentication();
  const isShowingCorrectAnswers = game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const timeToCountDown = isShowingCorrectAnswers ? game.timePerAnswer : game.timePerQuestion;

  const nudgeGame = async ({gameId}: {gameId: string}) => {
    const tokens = await getTokens();
    nudgeGameAction({gameId, tokens});
  };

  useEffect(() => {
    // all times are in seconds unless noted as `InMillis`
    const timeElapsedInMillis = Timestamp.now().toMillis() - game.startTime.seconds * 1000;
    const timeElapsed = timeElapsedInMillis / 1000;
    const timePerQuestionAndAnswer = game.timePerQuestion + game.timePerAnswer;

    if (isShowingCorrectAnswers) {
      const timeToStartNextQuestion = timePerQuestionAndAnswer * (game.currentQuestionIndex + 1);
      setTimeLeft(timeToStartNextQuestion - timeElapsed);
    } else {
      const timeToShowCurrentQuestionAnswer = timePerQuestionAndAnswer * (game.currentQuestionIndex) + game.timePerQuestion;
      setTimeLeft(timeToShowCurrentQuestionAnswer - timeElapsed);
    }
  }, [localCounter, game.startTime, game.currentQuestionIndex, game.timePerAnswer, game.timePerQuestion, isShowingCorrectAnswers]);

  // game leader nudge
  useEffect(() => {
    // whenever the game state or question changes
    // make a timeout to progress the question
    if (authUser.uid === game.leader.uid) {
      const timeoutIdTwo = setTimeout(() => nudgeGame({gameId}), timeLeft * 1000);
      // clear timeout on re-render to avoid memory leaks
      return () => clearTimeout(timeoutIdTwo);
    }
  }, [timeLeft, game.state, game.currentQuestionIndex, gameId, game.leader.uid, authUser.uid]);

  // game player nudge
  useEffect(() => {
    if (timeLeft % 2 < -1) {
      nudgeGame({gameId});
    }
  }, [timeLeft, gameId]);

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
          <div className="bg-gray-100 py-1 px-2 float-right">
            {displayTime < 10 && '0'}
            {displayTime}
          </div>
          {children}
        </div>
      </div>
    </>
  );
}
