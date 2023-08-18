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
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
import { FieldValue } from 'firebase-admin/firestore';
import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod';

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

  // update database to exit the game
  await gameRef.update({
    [`players.${authUser.uid}`]: FieldValue.delete(),
  });

  return NextResponse.json('successfully joined game', { status: 200 })
}