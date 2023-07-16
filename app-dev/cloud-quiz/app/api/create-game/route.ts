import { db } from '@/app/lib/firebase-server-initialization';
import { generateName } from '@/app/lib/name-generator';
import { getAuthenticatedUser } from '@/app/lib/server-side-auth'
import { gameStates } from '@/app/types';
import { Timestamp } from 'firebase-admin/firestore'; 
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

  const querySnapshot = await db.collection("questions").get();
  const questions = querySnapshot.docs.reduce((agg: any, doc: any, index: any) => {
    return { ...agg, [index]: doc.data() }
  }, {});
  if (!authUser) throw new Error('User must be signed in to start game');
  // create game with server endpoint

  const leader = {
    displayName: generateName(),
    uid: authUser.uid,
  };

  const startTime = Timestamp.now();

  const gameRef = await db.collection("games").add({
    questions,
    leader,
    players: {
      [leader.uid]: leader.displayName,
    },
    state: gameStates.NOT_STARTED,
    currentQuestionIndex: 0,
    startTime,
    timePerQuestion: 30,
    timePerAnswer: 10,
  });

  return NextResponse.json({ gameId: gameRef.id }, { status: 200 })
}