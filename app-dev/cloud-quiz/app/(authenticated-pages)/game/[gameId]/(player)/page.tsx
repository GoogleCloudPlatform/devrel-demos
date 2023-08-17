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

"use client"

import { useEffect } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { gameStates } from "@/app/types";
import PlayerLobby from "@/app/components/player-lobby";
import QuestionPanel from "@/app/components/question-panel";
import useGame from "@/app/hooks/use-game";
import ReturnToHomepagePanel from '@/app/components/return-to-homepage-panel';

export default function GamePage() {
  const authUser = useFirebaseAuthentication();
  const { game, gameId, gameRef, isShowingQuestion, currentQuestion, error: errorMessage } = useGame();

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
  }, [authUser, authUser.uid, game.players, gameId])

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
      {isShowingQuestion && (<QuestionPanel game={game} gameRef={gameRef} currentQuestion={currentQuestion} />)}
      {game.state === gameStates.NOT_STARTED && (<PlayerLobby game={game} gameRef={gameRef} />)}
    </>
  )
}
