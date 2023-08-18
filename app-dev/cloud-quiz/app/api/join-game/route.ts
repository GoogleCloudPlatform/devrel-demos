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
import { generateName } from '@/app/lib/name-generator';
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod';
import { badRequestResponse } from '@/app/lib/bad-request-response';
import { GameIdObject } from '@/app/types/zod-types';
import { authenticationFailedResponse } from '@/app/lib/authentication-failed-response';

export async function POST(request: NextRequest) {
  // Authenticate user
  let authUser;
  try {
    authUser = await getAuthenticatedUser(request);
  } catch (error) {
    return authenticationFailedResponse();
  }

  // Validate request
  const body = await request.json();
  const errorMessage = unknownValidator(body, GameIdObject);
  if (errorMessage) return badRequestResponse({errorMessage})
  const { gameId } = unknownParser(body, GameIdObject);
  const gameRef = await gamesRef.doc(gameId);

  // update database to join the game
  await gameRef.update({
    [`players.${authUser.uid}`]: generateName(),
  });

  return NextResponse.json('successfully joined game', { status: 200 })
}