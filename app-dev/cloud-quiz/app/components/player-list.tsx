"use client"

import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { Game } from "@/app/types";

export default function PlayerList({ game }: { game: Game }) {
  const authUser = useFirebaseAuthentication();

  return (<>
    <ul className="mt-5">
      {Object.values(game.players).map(displayName => (<li key={displayName}>
        {game.players[authUser.uid] === displayName && '*'}
        {displayName}
      </li>))}
    </ul>
  </>);
}
