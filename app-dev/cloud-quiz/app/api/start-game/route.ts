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

import { gamesRef } from '@/app/lib/firebase-server-initialization';
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
import { gameStates } from '@/app/types';
import { FieldValue } from 'firebase-admin/firestore';
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  // Authenticate user
  let authUser;

  try {
    authUser = await getAuthenticatedUser(request);
  } catch (error) {
    console.error({ error });
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: 'authentication failed' }),
      { status: 401, headers: { 'content-type': 'application/json' } }
    )
  }

  // Validate request
  const { gameId } = await request.json();

  if (!gameId) {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: 'no game id provided' }),
      { status: 400, headers: { 'content-type': 'application/json' } }
    )
  }

  const gameRef = await gamesRef.doc(gameId);
  const gameDoc = await gameRef.get();
  const game = gameDoc.data()

  if (game.leader.uid !== authUser.uid) {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: 'no game found' }),
      { status: 404, headers: { 'content-type': 'application/json' } }
    )
  }

  // update database to start the game
  await gameRef.update({
    state: gameStates.AWAITING_PLAYER_ANSWERS,
    startTime: FieldValue.serverTimestamp(),
  });

  // start automatic question progression
  async function showQuestion() {
    await new Promise(resolve => setTimeout(resolve, game.timePerQuestion * 1000));
    await gameRef.update({
      state: gameStates.SHOWING_CORRECT_ANSWERS,
    });
    showAnswers();
  }

  async function showAnswers() {
    const gameDoc = await gameRef.get();
    const game = gameDoc.data();
    await new Promise(resolve => setTimeout(resolve, game.timePerAnswer * 1000));
    if (game.currentQuestionIndex < Object.keys(game.questions).length - 1) {
      await gameRef.update({
        state: gameStates.AWAITING_PLAYER_ANSWERS,
        currentQuestionIndex: game.currentQuestionIndex + 1,
      });
      showQuestion();
    } else {
      await gameRef.update({
        state: gameStates.GAME_OVER,
      });
    }
  }

  showQuestion(); // starts first question

  return NextResponse.json('successfully started game', { status: 200 })
}