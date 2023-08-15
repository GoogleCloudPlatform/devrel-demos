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

import { DocumentReference } from "firebase/firestore";
import ExitGameButton from "@/app/components/exit-game-button";
import PlayerList from "@/app/components/player-list";
import { Game } from "@/app/types";
import ShareLinkPanel from "@/app/components/share-link-panel";
import { useState } from "react";

export default function PlayerLobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {

  const [showSharePanel, setShowSharePanel] = useState<Boolean>(false);

  return (
    <>
      {/* <ExitGameButton gameRef={gameRef} /> */}

      <center>
        {showSharePanel ? (
          <>
            <button onClick={() => setShowSharePanel(false)} className={`border m-2 mt-10 p-2`}>Hide Share Panel</button>
            <ShareLinkPanel gameRef={gameRef} />
          </>
        ) : (<button onClick={() => setShowSharePanel(true)} className={`border m-10 p-2`}>Invite Others to Join</button>)}
        <PlayerList game={game} />
      </center>
    </>
  )
}
