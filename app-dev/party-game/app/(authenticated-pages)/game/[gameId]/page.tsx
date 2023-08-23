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

'use client';

import {gameStates} from '@/app/types';
import Lobby from '@/app/components/lobby';
import QuestionPanel from '@/app/components/question-panel';
import useGame from '@/app/hooks/use-game';
import ReturnToHomepagePanel from '@/app/components/return-to-homepage-panel';
import Scoreboard from '@/app/components/scoreboard';
import {db} from '@/app/lib/firebase-client-initialization';
import {doc} from 'firebase/firestore';

export default function GamePage() {
  const {game, gameId, isShowingQuestion, currentQuestion, error: errorMessage} = useGame();
  const gameRef = doc(db, 'games', gameId);

  if (errorMessage) {
    return (
      <ReturnToHomepagePanel>
        <h2>{errorMessage}</h2>
      </ReturnToHomepagePanel>
    );
  }

  return (
    <>
      {(game.state === gameStates.GAME_OVER) && (<>
        <ReturnToHomepagePanel>
          <h2>Game Over</h2>
        </ReturnToHomepagePanel>
        <Scoreboard />
      </>)}
      {gameRef && <>
        {isShowingQuestion && (<QuestionPanel game={game} gameRef={gameRef} currentQuestion={currentQuestion} />)}
        {game.state === gameStates.NOT_STARTED && (<Lobby game={game} gameId={gameId} />)}
      </>}
    </>
  );
}
