"use client"

import { DocumentReference } from "firebase/firestore";
import StartGameButton from "@/app/components/start-game-button";
import DeleteGameButton from "@/app/components/delete-game-button";
import PlayerList from "./player-list";
import { Game } from "@/app/types";
import useFirebaseAuthentication from "../hooks/use-firebase-authentication";
import ShareLinkPanel from "./share-link-panel";

export default function PlayerLobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {

  const authUser = useFirebaseAuthentication();

  return (
    <div className="grid grid-cols-2">
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
