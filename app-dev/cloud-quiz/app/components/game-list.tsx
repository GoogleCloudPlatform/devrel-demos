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

import Link from "next/link";
import useActiveGameList from "../hooks/use-active-game-list";

export default function GameList() {
  const {activeGameList} = useActiveGameList();

  return (
    <div className="p-2 mx-auto max-w-2xl">
      {activeGameList.length > 0 ? activeGameList.map(game => (
        <div key={game.id} className={`border mt-5 p-2 rounded-md`}>
          <Link href={`/game/${game.id}`}>Join Game - {game.id}</Link>
        </div>
      )) : (<center className="mt-20">
        There are currently no games in progress.
      </center>)}
    </div>
  )
}
