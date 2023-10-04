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

import {gamesRef} from '@/app/lib/firebase-server-initialization';
import {GameIdSchema, GameSchema, GameStateUpdate, GameStateUpdateSchema, Tokens, gameStates} from '@/app/types';
import {FieldValue} from 'firebase-admin/firestore';
import {validateTokens} from '@/app/lib/server-token-validator';

export async function nudgeGameAction({gameId, desiredState, tokens}: { gameId: string, desiredState: GameStateUpdate, tokens: Tokens }) {
  const authUser = await validateTokens(tokens);

  // Validate request
  // Will throw an error if not a string
  GameIdSchema.parse(gameId);
  GameStateUpdateSchema.parse(desiredState);

  const gameRef = await gamesRef.doc(gameId);
  const gameDoc = await gameRef.get();
  const game = GameSchema.parse(gameDoc.data());

  if (game.leader.uid !== authUser.uid) {
    // Respond with JSON indicating no game was found
    throw new Error('Only the leader of this game may advance this game.');
  }

  const totalNumberOfQuestions = Object.keys(game.questions).length;
  const finalQuestionIndex = totalNumberOfQuestions - 1;

  const nextQuestionIndex = game.currentQuestionIndex + 1;

  const {NOT_STARTED, AWAITING_PLAYER_ANSWERS, GAME_OVER, SHOWING_CORRECT_ANSWERS} = gameStates;

  // if the game is already in the desired state, no further action required
  if (game.state === desiredState.state && game.currentQuestionIndex === desiredState.currentQuestionIndex) {
    throw new Error('Desired state is same as current state. No changes to be made.');
  }

  switch (game.state) {
    case GAME_OVER:
      throw new Error('The game is over. No game progression is allowed.');
    case NOT_STARTED:
      if (desiredState.state === AWAITING_PLAYER_ANSWERS && desiredState.currentQuestionIndex === 0) {
        await gameRef.update({
          state: AWAITING_PLAYER_ANSWERS,
          currentQuestionIndex: 0,
          currentStateStartTime: FieldValue.serverTimestamp(),
        });
        return;
      }
      throw new Error('The only allowed game progression when NOT_STARTED is to AWAITING_PLAYER_ANSWERS');
    case SHOWING_CORRECT_ANSWERS:
      if (desiredState.currentQuestionIndex === nextQuestionIndex) {
        if (game.currentQuestionIndex === finalQuestionIndex) {
          await gameRef.update({
            state: GAME_OVER,
            currentStateStartTime: FieldValue.serverTimestamp(),
          });
          return;
        }
        await gameRef.update({
          state: AWAITING_PLAYER_ANSWERS,
          currentQuestionIndex: nextQuestionIndex,
          currentStateStartTime: FieldValue.serverTimestamp(),
        });
        return;
      }
      throw new Error('The only allowed game progression when SHOWING_CORRECT_ANSWERS is to AWAITING_PLAYER_ANSWERS on the next question');
    case AWAITING_PLAYER_ANSWERS:
      if (desiredState.state === SHOWING_CORRECT_ANSWERS && desiredState.currentQuestionIndex === game.currentQuestionIndex) {
        await gameRef.update({
          state: SHOWING_CORRECT_ANSWERS,
          currentStateStartTime: FieldValue.serverTimestamp(),
        });
        return;
      }
      throw new Error('The only allowed game progression when AWAITING_PLAYER_ANSWERS is to SHOWING_CORRECT_ANSWERS');
  }
}
