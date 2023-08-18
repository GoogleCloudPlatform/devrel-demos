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

import { useEffect, useState } from "react";
import { db } from "@/app/lib/firebase-client-initialization"
import { Game, emptyGame, gameStates } from "@/app/types";
import { doc, onSnapshot } from "firebase/firestore";
import { usePathname } from "next/navigation";
import useFirebaseAuthentication from "./use-firebase-authentication";

const useGame = () => {
  const pathname = usePathname();
  const gameId = pathname.split('/')[2];
  const gameRef = doc(db, "games", gameId);
  const [game, setGame] = useState<Game>(emptyGame);
  const [error, setErrorMessage] = useState<string>("");
  const authUser = useFirebaseAuthentication();

  useEffect(() => {
    const playerIdList = Object.keys(game.players);

    const joinGame = async () => {
      if (!playerIdList.includes(authUser.uid)) {
        const token = await authUser.getIdToken();
        console.log('joining the game')
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
    };

    if (game.leader.uid && authUser.uid && game.leader.uid !== authUser.uid) {
      joinGame();
    }

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authUser.uid, game.leader.uid, gameId]);

  useEffect(() => {
    const unsubscribe = onSnapshot(gameRef, (doc) => {
      const game = doc.data() as Game;
      if (game) {
        setGame(game);
      } else {
        setErrorMessage(`Game ${gameId} was not found.`)
      }
    });

    return () => {
      unsubscribe();
    };
  }, [authUser.uid, gameId, gameRef])

  return {
    gameRef,
    gameId,
    game,
    isShowingQuestion: game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS,
    currentQuestion: game.questions[game.currentQuestionIndex],
    error,
  }
}

export default useGame;