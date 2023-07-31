"use client"

import { DocumentReference } from "firebase/firestore";
import StartGameButton from "@/app/components/start-game-button";
import DeleteGameButton from "@/app/components/delete-game-button";
import ExitGameButton from "@/app/components/exit-game-button";
import PlayerList from "./player-list";
import { Game } from "@/app/types";
import useFirebaseAuthentication from "../hooks/use-firebase-authentication";

export default function Lobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {

  const authUser = useFirebaseAuthentication();

  return (
    <>
      <PlayerList game={game} />
      {authUser.uid === game.leader.uid ? (<>
        <StartGameButton gameRef={gameRef} />
        <DeleteGameButton gameRef={gameRef} />
      </>) : (<>
        <ExitGameButton gameRef={gameRef} />
      </>)}
    </>
  )
}
