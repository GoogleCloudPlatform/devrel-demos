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

import { unknownParser, unknownValidator } from '@/app/lib/zod-parser';
import { gamesRef } from '@/app/lib/firebase-server-initialization';
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
import { gameStates } from '@/app/types';
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod';
import { AnswerSelectionWithGameId } from '@/app/types/zod-types';
import { badRequestResponse } from '@/app/lib/bad-request-response';
import { authenticationFailedResponse } from '@/app/lib/authentication-failed-response';

export async function POST(request: NextRequest) {
  let authUser;
  try {
    authUser = await getAuthenticatedUser(request);
  } catch (error) {
    return authenticationFailedResponse();
  }

  // Validate request
  const body = await request.json();
  const errorMessage = unknownValidator(body, AnswerSelectionWithGameId);
  console.log({errorMessage});
  if (errorMessage) return badRequestResponse({errorMessage})
  const { gameId, answerSelection } = unknownParser(body, AnswerSelectionWithGameId);

  const gameRef = await gamesRef.doc(gameId);
  const gameDoc = await gameRef.get();
  const game = gameDoc.data()

  if (game.state !== gameStates.AWAITING_PLAYER_ANSWERS) {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: `answering is not allowed during ${game.state}` }),
      { status: 403, headers: { 'content-type': 'application/json' } }
    )
  }


  // answerSelection must be an array of booleans as long as the game question answers
  const currentQuestion = game.questions[game.currentQuestionIndex];
  const isCorrectLength = answerSelection.length === currentQuestion.answers.length

  const isBoolean = (value: boolean) => value === true || value === false;
  const answerSelectionIsValid = answerSelection.every(isBoolean);

  if (!isCorrectLength || !answerSelectionIsValid) {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: 'answer selection must be an array of booleans as long as the game question answers' }),
      { status: 400, headers: { 'content-type': 'application/json' } }
    )
  }

  // update database to start the game
  await gameRef.update({
    [`questions.${game.currentQuestionIndex}.playerGuesses.${authUser.uid}`]: answerSelection,
  });

  return NextResponse.json('successfully started game', { status: 200 })
}