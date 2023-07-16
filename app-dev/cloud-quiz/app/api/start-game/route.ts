import { db } from '@/app/lib/firebase-server-initialization';
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

  const gameRef = await db.collection("games").doc(gameId);
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
    currentTimerStart: FieldValue.serverTimestamp(),
  });

  // start automatic question progression
  async function onQuestionTimeExpired() {
    await gameRef.update({
      state: gameStates.SHOWING_CORRECT_ANSWERS,
    });
    setTimeout(onAnswerTimeExpired, game.timePerAnswer * 1000)
  }

  async function onAnswerTimeExpired() {
    const gameDoc = await gameRef.get();
    const game = gameDoc.data();
    if (game.currentQuestionIndex < Object.keys(game.questions).length - 1) {
      await gameRef.update({
        state: gameStates.AWAITING_PLAYER_ANSWERS,
        currentQuestionIndex: game.currentQuestionIndex + 1,
      });
      setTimeout(onQuestionTimeExpired, game.timePerQuestion * 1000)
    } else {
      await gameRef.update({
        state: gameStates.GAME_OVER,
      });
    }
  }

  setTimeout(onQuestionTimeExpired, game.timePerQuestion * 1000)

  return NextResponse.json('successfully started game', { status: 200 })
}