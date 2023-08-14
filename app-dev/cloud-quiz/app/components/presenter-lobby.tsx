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
import StartGameButton from "@/app/components/start-game-button";
import DeleteGameButton from "@/app/components/delete-game-button";
import PlayerList from "./player-list";
import { Game } from "@/app/types";
import useFirebaseAuthentication from "../hooks/use-firebase-authentication";
import ShareLinkPanel from "./share-link-panel";

export default function PresenterLobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {

  const authUser = useFirebaseAuthentication();

  return (
    <div className="grid lg:grid-cols-2">
      <div className="mt-20">
        <PlayerList game={game} />
      </div>
      <center>
        {authUser.uid === game.leader.uid && (<div className="my-20">
          <StartGameButton gameRef={gameRef} />
        </div>)}
        <ShareLinkPanel gameRef={gameRef} />
        {authUser.uid === game.leader.uid && <DeleteGameButton gameRef={gameRef} />}
      </center>
    </div>
  )
}
