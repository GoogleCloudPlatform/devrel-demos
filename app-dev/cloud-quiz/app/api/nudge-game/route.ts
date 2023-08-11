import { gamesRef } from '@/app/lib/firebase-server-initialization';
import { timeCalculator } from '@/app/lib/time-calculator';
import { gameStates } from '@/app/types';
import { Timestamp } from 'firebase-admin/firestore';
import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
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
  const gameDoc = await gameRef.get();
  const game = gameDoc.data();

  // force the game state to move to where the game should be
  const {
    timeElapsed,
    timePerQuestionAndAnswer,
    isTimeToShowAnswer,
    isTimeToStartNextQuestion,
  } = timeCalculator({ currentTimeInSeconds: Timestamp.now().seconds, game })

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

  return NextResponse.json('successfully started game', { status: 200 })
}