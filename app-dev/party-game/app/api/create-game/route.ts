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
import {gamesRef, questionsRef} from '@/app/lib/firebase-server-initialization';
import {generateName} from '@/app/lib/name-generator';
import {getAuthenticatedUser} from '@/app/lib/server-side-auth';
import {Game, Question, QuestionSchema, gameStates} from '@/app/types';
import {QueryDocumentSnapshot, Timestamp} from 'firebase-admin/firestore';
import {NextRequest, NextResponse} from 'next/server';
import {authenticationFailedResponse} from '@/app/lib/authentication-failed-response';
import {GameSettingsSchema} from '@/app/types';
import {badRequestResponse} from '@/app/lib/bad-request-response';

export async function POST(request: NextRequest) {
  let authUser;
  try {
    authUser = await getAuthenticatedUser(request);
  } catch (error) {
    return authenticationFailedResponse();
  }

  // Validate request
  const body = await request.json();
  const errorMessage = unknownValidator(body, GameSettingsSchema);
  if (errorMessage) return badRequestResponse({errorMessage});
  const {timePerQuestion, timePerAnswer} = unknownParser(body, GameSettingsSchema);


  const querySnapshot = await questionsRef.get();
  const validQuestionsArray = querySnapshot.docs.reduce((agg: Question[], doc: QueryDocumentSnapshot) => {
    const question = doc.data();
    const errorMessage = unknownValidator(question, QuestionSchema);
    if (errorMessage) {
      console.warn(`WARNING: The question "${question?.prompt}" [Firestore ID: ${doc.id}] has an issue and will not be added to the game.`);
      return agg;
    }
    return [...agg, question];
  }, []);
  const questions = {...validQuestionsArray};
  if (!authUser) throw new Error('User must be signed in to start game');
  // create game with server endpoint

  const leader = {
    displayName: generateName(),
    uid: authUser.uid,
  };

  const startTime = Timestamp.now();

  const newGame: Game= {
    questions,
    leader,
    players: {},
    state: gameStates.NOT_STARTED,
    currentQuestionIndex: 0,
    startTime,
    timePerQuestion: timePerQuestion + 1, // add one for padding between questions
    timePerAnswer: timePerAnswer + 1, // add one for padding between questions
  };

  const gameRef = await gamesRef.add(newGame);

  return NextResponse.json({gameId: gameRef.id}, {status: 200});
}
