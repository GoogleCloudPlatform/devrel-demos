"use client"

import { useEffect } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { gameStates } from "@/app/types";
import Lobby from "@/app/components/lobby";
import QuestionPanel from "@/app/components/question-panel";
import { usePathname } from 'next/navigation';
import Link from "next/link";
import useGame from "@/app/hooks/use-game";

export default function GamePage() {
  const authUser = useFirebaseAuthentication();
  const pathname = usePathname();
  const gameId = pathname.split('/')[2];
  const { game, gameRef, error: errorMessage } = useGame(gameId);

  const showingQuestion = game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const currentQuestion = game.questions[game.currentQuestionIndex];

  useEffect(() => {
    if (authUser.uid && Object.keys(game.players)) {
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
        <br />
        <Link href="/">Return to Home Page</Link>
      </div>}
      {showingQuestion && gameRef && (<>
        <QuestionPanel game={game} gameRef={gameRef} currentQuestion={currentQuestion} />
      </>)}
      {game.state === gameStates.NOT_STARTED && gameRef && (<>
        <Lobby game={game} gameRef={gameRef} />
      </>)}
    </>
  )
}
