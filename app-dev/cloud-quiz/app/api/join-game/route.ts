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
import { generateName } from '@/app/lib/name-generator';
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
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

  // update database to join the game
  await gameRef.update({
    [`players.${authUser.uid}`]: generateName(),
  });

  return NextResponse.json('successfully joined game', { status: 200 })
}