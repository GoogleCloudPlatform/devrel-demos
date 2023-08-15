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

import { gamesRef, questionsRef } from '@/app/lib/firebase-server-initialization';
import { gameFormValidator } from '@/app/lib/game-form-validator';
import { generateName } from '@/app/lib/name-generator';
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
import { Question, gameStates } from '@/app/types';
import { QueryDocumentSnapshot, Timestamp } from 'firebase-admin/firestore'; 
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
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
  const { timePerQuestion, timePerAnswer }: { timePerQuestion: number, timePerAnswer: number } = await request.json();

  const errorMessage = gameFormValidator({timePerQuestion, timePerAnswer});

  if (errorMessage) {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: errorMessage }),
      { status: 400, headers: { 'content-type': 'application/json' } }
    )
  }

  const querySnapshot = await questionsRef.get();
  const questions = querySnapshot.docs.reduce((agg: Question[], doc: QueryDocumentSnapshot, index: number) => {
    return { ...agg, [index]: doc.data() as Question }
  }, {});
  if (!authUser) throw new Error('User must be signed in to start game');
  // create game with server endpoint

  const leader = {
    displayName: generateName(),
    uid: authUser.uid,
  };

  const startTime = Timestamp.now();

  const gameRef = await gamesRef.add({
    questions,
    leader,
    players: {},
    state: gameStates.NOT_STARTED,
    currentQuestionIndex: 0,
    startTime,
    timePerQuestion,
    timePerAnswer,
  });

  return NextResponse.json({ gameId: gameRef.id }, { status: 200 })
}