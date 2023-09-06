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

'use server';

import {app, gamesRef} from '@/app/lib/firebase-server-initialization';
import {GameIdSchema, gameStates} from '@/app/types';
import {getAppCheck} from 'firebase-admin/app-check';
import {getAuth} from 'firebase-admin/auth';
import {Timestamp} from 'firebase-admin/firestore';

export async function nudgeGameAction({gameId, token, appCheckToken}: {gameId: string, token: string, appCheckToken: string}) {
  await getAppCheck().verifyToken(appCheckToken);
  await getAuth(app).verifyIdToken(token);

  // Validate request
  // Will throw an error if not a string
  GameIdSchema.parse(gameId);

  const gameRef = await gamesRef.doc(gameId);
  const gameDoc = await gameRef.get();
  const game = gameDoc.data();

  // force the game state to move to where the game should be

  const timeElapsedInMillis = Timestamp.now().toMillis() - game.startTime.seconds * 1000;
  const timeElapsed = timeElapsedInMillis / 1000;
  const timePerQuestionAndAnswer = game.timePerQuestion + game.timePerAnswer;

  const totalNumberOfQuestions = Object.keys(game.questions).length;
  const finalQuestionIndex = totalNumberOfQuestions - 1;
  const correctQuestionIndex = Math.floor(timeElapsed / timePerQuestionAndAnswer);
  if (correctQuestionIndex > finalQuestionIndex) {
    await gameRef.update({
      state: gameStates.GAME_OVER,
      currentQuestionIndex: finalQuestionIndex,
    });
    return;
  }

  const timeThisQuestionStarted = correctQuestionIndex * timePerQuestionAndAnswer;
  const shouldBeAcceptingAnswers = timeElapsed - timeThisQuestionStarted < game.timePerQuestion;
  const correctState = shouldBeAcceptingAnswers ? gameStates.AWAITING_PLAYER_ANSWERS : gameStates.SHOWING_CORRECT_ANSWERS;

  await gameRef.update({
    state: correctState,
    currentQuestionIndex: correctQuestionIndex,
  });
}
