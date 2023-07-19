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
  const { gameId, newAnswerSelection } = await request.json();

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

  if (game.state !== gameStates.AWAITING_PLAYER_ANSWERS) {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: `answering is not allowed during ${game.state}` }),
      { status: 403, headers: { 'content-type': 'application/json' } }
    )
  }


  // newAnswerSelection must be an array of booleans as long as the game question answers
  const currentQuestion = game.questions[game.currentQuestionIndex];
  const isCorrectLength = newAnswerSelection.length === currentQuestion.answers.length

  const isBoolean = (value: boolean) => value === true || value === false;
  const answerSelectionIsValid = newAnswerSelection.every(isBoolean);

  if (!isCorrectLength || !answerSelectionIsValid) {
    // Respond with JSON indicating an error message
    return new NextResponse(
      JSON.stringify({ success: false, message: 'answer selection must be an array of booleans as long as the game question answers' }),
      { status: 400, headers: { 'content-type': 'application/json' } }
    )
  }

  // update database to start the game
  await gameRef.update({
    [`questions.${game.currentQuestionIndex}.playerGuesses.${authUser.uid}`]: newAnswerSelection,
  });

  return NextResponse.json('successfully started game', { status: 200 })
}