import { db } from '@/app/lib/firebase-server-initialization';
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
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

  const gameRef = await db.collection("games").doc(gameId);
  const gameDoc = await gameRef.get();
  const game = gameDoc.data()

  if (game.leader.uid !== authUser.uid) {
    // Respond with JSON indicating no game was found
    return new NextResponse(
      JSON.stringify({ success: false, message: 'no game found' }),
      { status: 404, headers: { 'content-type': 'application/json' } }
    )
  }

  // update database to delete the game
  await gameRef.delete();

  return NextResponse.json('successfully joined game', { status: 200 })
}