"use client"

import { useEffect } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { gameStates } from "@/app/types";
import BigScreenLobby from "@/app/components/big-screen-lobby";
import QuestionPanel from "@/app/components/question-panel";
import useGame from "@/app/hooks/use-game";
import ReturnToHomepagePanel from '@/app/components/return-to-homepage-panel';

export default function GamePage() {
  const authUser = useFirebaseAuthentication();
  const { game, gameId, gameRef, isShowingQuestion, currentQuestion, error: errorMessage } = useGame();

  useEffect(() => {
    if (authUser.uid) {
      const exitGame = async () => {
        if (Object.keys(game.players).includes(authUser.uid)) {
          const token = await authUser.getIdToken();
          await fetch('/api/exit-game', {
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

      exitGame();
    }
  }, [authUser.uid])

  if (errorMessage) {
    return (
      <ReturnToHomepagePanel>
        <h2>{errorMessage}</h2>
      </ReturnToHomepagePanel>
    )
  }

  return (
    <>
      {(game.state === gameStates.GAME_OVER) && (
        <ReturnToHomepagePanel>
          <h2>Game Over</h2>
        </ReturnToHomepagePanel>
      )}
      {isShowingQuestion && gameRef && (<>
        <QuestionPanel game={game} gameRef={gameRef} currentQuestion={currentQuestion} />
      </>)}
      {game.state === gameStates.NOT_STARTED && gameRef && (<>
        <BigScreenLobby game={game} gameRef={gameRef} />
      </>)}
    </>
  )
}
