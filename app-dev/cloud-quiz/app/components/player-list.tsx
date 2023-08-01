"use client"

import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { Game } from "@/app/types";
import "./player-list.css";

export default function PlayerList({ game }: { game: Game }) {
  const authUser = useFirebaseAuthentication();

  const currentPlayerName = game.players[authUser.uid];

  return (<>
    {currentPlayerName && (<div className="mt-5">
      <div className="player-list-item">
        {currentPlayerName}
      </div>
      {currentPlayerName === currentPlayerName && ' <-- You!'}
    </div>)}
    <div className="mt-5">
      {Object.values(game.players).sort((a) => (a === currentPlayerName ? -1 : 0)).map(displayName => (<div key={displayName} className="player-list-item">
        {displayName}
      </div>))}
    </div>
  </>);
}
