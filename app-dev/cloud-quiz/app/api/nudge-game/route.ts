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

import {unknownParser, unknownValidator} from '@/app/lib/zod-parser';
import {gamesRef} from '@/app/lib/firebase-server-initialization';
import {timeCalculator} from '@/app/lib/time-calculator';
import {gameStates} from '@/app/types';
import {Timestamp} from 'firebase-admin/firestore';
import {NextRequest, NextResponse} from 'next/server';
import {badRequestResponse} from '@/app/lib/bad-request-response';
import {GameIdObject} from '@/app/types/zod-types';

export async function POST(request: NextRequest) {
  // Validate request
  const body = await request.json();
  const errorMessage = unknownValidator(body, GameIdObject);
  if (errorMessage) return badRequestResponse({errorMessage});
  const {gameId} = unknownParser(body, GameIdObject);

  const gameRef = await gamesRef.doc(gameId);
  const gameDoc = await gameRef.get();
  const game = gameDoc.data();

  // force the game state to move to where the game should be
  const {
    timeElapsed,
    timePerQuestionAndAnswer,
    isTimeToShowAnswer,
    isTimeToStartNextQuestion,
  } = timeCalculator({currentTimeInMillis: Timestamp.now().toMillis(), game});

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

  return NextResponse.json('successfully nudged game', {status: 200});
}
