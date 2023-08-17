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

import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import useGame from "@/app/hooks/use-game";
import '@/app/components/player-list.css';

export default function Scoreboard() {
  const authUser = useFirebaseAuthentication();
  const { game } = useGame();

  // create a list of all players
  const arraysAreEqual = (a: Boolean[], b: Boolean[]) => {
    return a.every((val, index) => val === b[index]);
  }

  const playerScoresObject = Object.values(game.questions).reduce((playerScores: { [key: string]: { score: number, displayName: string, uid: string }; }, question) => {
    const correctAnswerArray = question.answers.map(answer => answer.isCorrect);
    let newPlayerScores = playerScores;
    // for each question, go through every guess
    Object.entries(question.playerGuesses).forEach(([uid, playerGuess]) => {
      const previousPlayerScore = playerScores[uid]?.score || 0;
      // if a player's guess is correct, add 1 point to their score
      const currentQuestionScore = arraysAreEqual(correctAnswerArray, playerGuess) ? 1 : 0;
      const score = previousPlayerScore + currentQuestionScore;
      newPlayerScores = {
        ...newPlayerScores,
        [uid]: { displayName: game.players[uid], score, uid },
      }
    });
    return newPlayerScores;
  }, {});

  const playerScores = Object.values(playerScoresObject).sort(function (a, b) {
    // higher score goes first
    // otherwise, sort alphabetically
    if (a.score > b.score) return -1;
    if (a.score < b.score) return 1;
    return a.displayName.localeCompare(b.displayName);
  });

  const currentPlayer = playerScoresObject[authUser.uid];

  return (
    <div className="mt-5 w-fit m-auto">
      <center className='mt-10'>
        Full Scoreboard
      </center>
      {playerScores.map((playerScore) => (<div key={playerScore.uid} className="player-list-item relative" style={{ display: 'block' }}>
        <div className='flex justify-between'>
          <div className='pr-4'>{playerScore.displayName}</div>
          <div>{playerScore.score}</div>
        </div>
        <div className='text-black z-50 absolute left-full min-w-fit whitespace-nowrap top-0 h-full flex p-1'>
          <div className='m-auto'>
            {currentPlayer?.uid === playerScore.uid && ' ← You!'}
          </div>
        </div>
      </div>))}
    </div>
  )
}
