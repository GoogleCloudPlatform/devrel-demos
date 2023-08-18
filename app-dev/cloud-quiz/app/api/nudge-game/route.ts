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

import { unknownParser } from '@/app/lib/unknown-parser';
import { gamesRef } from '@/app/lib/firebase-server-initialization';
import { timeCalculator } from '@/app/lib/time-calculator';
import { gameStates } from '@/app/types';
import { Timestamp } from 'firebase-admin/firestore';
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod';

export async function POST(request: NextRequest) {
  // Validate request
  // Validate request
  const Body = z.object({
    gameId: z.string(),
  });

  let parsedBody;

  try {
    const body = await request.json();
    parsedBody = unknownParser(body, Body);
  } catch (error) {
    // return the first error
    if (error instanceof Error) {
      // Respond with JSON indicating an error message
      const {message} = error;
      return new NextResponse(
        JSON.stringify({ success: false, message }),
        { status: 400, headers: { 'content-type': 'application/json' } }
      );
    }
    throw error;
  }

  const { gameId } = parsedBody;

  const gameRef = await gamesRef.doc(gameId);
  const gameDoc = await gameRef.get();
  const game = gameDoc.data();

  // force the game state to move to where the game should be
  const {
    timeElapsed,
    timePerQuestionAndAnswer,
    isTimeToShowAnswer,
    isTimeToStartNextQuestion,
  } = timeCalculator({ currentTimeInMillis: Timestamp.now().toMillis(), game })

  const totalNumberOfQuestions = Object.keys(game.questions).length;

  if (isTimeToStartNextQuestion) {
    if (game.currentQuestionIndex < totalNumberOfQuestions - 1) {
      await gameRef.update({
        state: gameStates.AWAITING_PLAYER_ANSWERS,
        currentQuestionIndex: Math.min(Math.floor(timeElapsed / timePerQuestionAndAnswer), totalNumberOfQuestions - 1),
      });
    } else {
      await gameRef.update({
        state: gameStates.GAME_OVER,
      });
    }
  } else if (isTimeToShowAnswer) {
    await gameRef.update({
      state: gameStates.SHOWING_CORRECT_ANSWERS,
    });
  }

  return NextResponse.json('successfully nudged game', { status: 200 })
}