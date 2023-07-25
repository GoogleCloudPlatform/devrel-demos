"use client"

// Import the functions you need from the SDKs you need
import { db } from "@/app/lib/firebase-client-initialization";
import { onSnapshot, doc, DocumentReference } from "firebase/firestore";
import { useEffect, useState } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { Game, emptyGame, gameStates } from "@/app/types";
import Lobby from "@/app/components/lobby";
import QuestionPanel from "@/app/components/question-panel";
import { usePathname } from 'next/navigation';
import Link from "next/link";

export default function GamePage() {
  const [gameRef, setGameRef] = useState<DocumentReference>();
  const [game, setGame] = useState<Game>(emptyGame);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const authUser = useFirebaseAuthentication();
  const pathname = usePathname();
  const gameId = pathname.split('/')[2];

  const showingQuestion = game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const currentQuestion = game.questions[game.currentQuestionIndex];

  useEffect(() => {
    const gameRef = doc(db, "games", gameId);
    const unsubscribe = onSnapshot(gameRef, (doc) => {
      const game = doc.data() as Game;
      if (game) {
        setGame(game);
        setGameRef(gameRef);
      } else {
        setErrorMessage(`Game ${gameId} was not found.`)
      }
    });
    return unsubscribe;
  }, [gameId])

  useEffect(() => {
    if (authUser.uid && Object.keys(game.players).length > 0) {
      const joinGame = async () => {
        if (!Object.keys(game.players).includes(authUser.uid)) {
          const token = await authUser.getIdToken();
          await fetch('/api/join-game', {
            method: 'POST',
            body: JSON.stringify({ gameId }),
            headers: {
              Authorization: token,
            }
          }).catch(error => {
            console.error({ error })
          });
        }
      }

      joinGame();
    }
  }, [authUser.uid, game.players])

  if (errorMessage) {
    return (
      <>
        {errorMessage}
        <div>
          <Link href="/">Return to Homepage</Link>
        </div>
      </>
    )
  }

  return (
    <>
      <div>
        Your Player Name: {game.players[authUser.uid]}
      </div>
      <div>
        Game ID: {gameId}
      </div>
      {(game.state === gameStates.GAME_OVER) && <div>
        {gameStates.GAME_OVER}
        <Link href="/">Return to Home Page</Link>
      </div>}
      {showingQuestion && gameRef && (<>
        <QuestionPanel game={game} gameRef={gameRef} currentQuestion={currentQuestion} />
      </>)}
      {game.state === gameStates.NOT_STARTED && gameRef && (<>
        <Lobby game={game} gameRef={gameRef} setGameRef={setGameRef} />
      </>)}
    </>
  )
}
