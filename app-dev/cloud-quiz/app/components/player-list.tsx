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

import useFirebaseAuthentication from '@/app/hooks/use-firebase-authentication';
import {Game} from '@/app/types';
import './player-list.css';

export default function PlayerList({game}: { game: Game }) {
  const authUser = useFirebaseAuthentication();

  const currentPlayerName = game.players[authUser.uid];

  // sort the names so they are in alphabetical order
  // then sort to put the current player first
  const playerDisplayNames = Object.values(game.players).sort().sort((a) => (a === currentPlayerName ? -1 : 0));

  if (playerDisplayNames.length < 1) {
    return 'No players have joined the game yet.';
  }

  return (<center className="mx-auto max-w-7xl">
    {currentPlayerName && (<div className="mt-5">
      <div className="player-list-item">
        {currentPlayerName}
      </div>
      {' ← You!'}
    </div>)}
    <div className="mt-5">
      {playerDisplayNames.map((displayName) => (<div key={displayName} className="player-list-item">
        {displayName}
      </div>))}
    </div>
  </center>);
}
