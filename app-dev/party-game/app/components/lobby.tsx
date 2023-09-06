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

import StartGameButton from '@/app/components/start-game-button';
import DeleteGameButton from '@/app/components/delete-game-button';
import PlayerList from './player-list';
import {Game} from '@/app/types';
import useFirebaseAuthentication from '@/app/hooks/use-firebase-authentication';
import ShareLinkPanel from './share-link-panel';
import {useState} from 'react';

export default function Lobby({game, gameId}: { game: Game; gameId: string }) {
  const authUser = useFirebaseAuthentication();
  const [showSharePanel, setShowSharePanel] = useState<boolean>(false);

  return (
    <div className="grid lg:grid-cols-2 mt-20">
      <center>
        <div className="lg:hidden">
          <button onClick={() => setShowSharePanel(!showSharePanel)} className={`border m-2 mt-10 p-2`}>
            {showSharePanel ? 'Hide Share Panel' : 'Invite Others to Join'}
          </button>
          {showSharePanel && <ShareLinkPanel gameId={gameId} />}
        </div>
        <div className="my-8">
          <PlayerList game={game} />
        </div>
      </center>
      <center>
        {authUser.uid === game.leader.uid && <StartGameButton gameId={gameId} />}
        <div className="hidden lg:block">
          <ShareLinkPanel gameId={gameId} />
        </div>
        {authUser.uid === game.leader.uid && <DeleteGameButton gameId={gameId} />}
      </center>
    </div>
  );
}
