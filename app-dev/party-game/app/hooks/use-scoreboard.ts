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

import useFirebaseAuthentication from './use-firebase-authentication';
import useGame from './use-game';

const useScoreboard = () => {
  const authUser = useFirebaseAuthentication();
  const {game} = useGame();

  // create a list of all players
  const arraysAreEqual = (a: boolean[], b: boolean[]) => {
    return a.every((val, index) => val === b[index]);
  };

  const playerScoresObject = Object.values(game.questions).reduce((playerScores: { [key: string]: { score: number, displayName: string, uid: string }; }, question) => {
    const correctAnswerArray = question.answers.map((answer) => answer.isCorrect);
    let newPlayerScores = playerScores;
    // for each question, go through every guess
    if (question.playerGuesses) {
      Object.entries(question.playerGuesses).forEach(([uid, playerGuess]) => {
        const previousPlayerScore = playerScores[uid]?.score || 0;
        // if a player's guess is correct, add 1 point to their score
        const currentQuestionScore = arraysAreEqual(correctAnswerArray, playerGuess) ? 1 : 0;
        const score = previousPlayerScore + currentQuestionScore;
        newPlayerScores = {
          ...newPlayerScores,
          [uid]: {displayName: game.players[uid], score, uid},
        };
      });
    }
    return newPlayerScores;
  }, {});

  const currentPlayer = {
    ...playerScoresObject[authUser.uid],
    displayName: game.players[authUser.uid],
  };

  const playerScores = Object.values(playerScoresObject).sort((a, b) => {
    // higher score goes first
    if (a.score > b.score) return -1;
    if (a.score < b.score) return 1;
    // put the current player at the top of those with the same score
    if (a.uid === authUser.uid) return -1;
    if (b.uid === authUser.uid) return 1;
    // otherwise, sort alphabetically
    return a.displayName.localeCompare(b.displayName);
  });

  return {
    currentPlayer,
    playerScores,
  };
};

export default useScoreboard;
