"use client"

import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { Game } from "@/app/types";
import "./player-list.css";

export default function PlayerList({ game }: { game: Game }) {
  const authUser = useFirebaseAuthentication();

  const currentPlayerName = game.players[authUser.uid];

  // sort the names so the current player is first
  const playerDisplayNames = Object.values(game.players).sort((a) => (a === currentPlayerName ? -1 : 0));

  if (playerDisplayNames.length < 1) {
    return <div className="grid h-full place-items-center">
      No players have joined the game yet.
    </div>
  }

  return (<center className="mx-auto max-w-7xl">
    {currentPlayerName && (<div className="mt-5">
      <div className="player-list-item">
        {currentPlayerName}
      </div>
      {' ← You!'}
    </div>)}
    <div className="mt-5">
      {playerDisplayNames.map(displayName => (<div key={displayName} className="player-list-item">
        {displayName}
      </div>))}
    </div>
  </center>);
}
