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

import {app, gamesRef, questionsRef} from '@/app/lib/firebase-server-initialization';
import {generateName} from '@/app/lib/name-generator';
import {Game, GameSettings, Question, QuestionSchema, gameStates} from '@/app/types';
import {QueryDocumentSnapshot, Timestamp} from 'firebase-admin/firestore';
import {GameSettingsSchema} from '@/app/types';
import {getAuth} from 'firebase-admin/auth';

export async function createGameAction({gameSettings, token}: {gameSettings: GameSettings, token: string}): Promise<{gameId: string}> {
  const authUser = await getAuth(app).verifyIdToken(token);

  // Parse request (throw an error if not correct)
  const {timePerQuestion, timePerAnswer} = GameSettingsSchema.parse(gameSettings);

  const querySnapshot = await questionsRef.get();
  const validQuestionsArray = querySnapshot.docs.reduce((agg: Question[], doc: QueryDocumentSnapshot) => {
    let question = doc.data();
    try {
      question = QuestionSchema.parse(question);
      return [...agg, question];
    } catch (error) {
      console.warn(`WARNING: The question "${question?.prompt}" [Firestore ID: ${doc.id}] has an issue and will not be added to the game.`);
      return agg;
    }
  }, []);

  // convert array to object for Firebase
  const questions = {...validQuestionsArray};

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

  if (gameRef.id) return {gameId: gameRef.id};

  throw new Error('no gameId returned in the response');
}
