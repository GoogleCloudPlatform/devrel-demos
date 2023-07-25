"use client"

import { DocumentData, DocumentReference } from "firebase/firestore";
import StartGameButton from "@/app/components/start-game-button";
import ExitGameButton from "@/app/components/exit-game-button";
import { Dispatch, SetStateAction } from "react";
import PlayerList from "./player-list";
import { Game } from "@/app/types";
import useFirebaseAuthentication from "../hooks/use-firebase-authentication";

export default function Lobby({ game, gameRef, setGameRef }: { game: Game; gameRef: DocumentReference, setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>> }) {

const authUser = useFirebaseAuthentication();

  return (
    <>
      <PlayerList game={game} />
      {authUser.uid === game.leader.uid && <StartGameButton gameRef={gameRef} /> }
      <ExitGameButton setGameRef={setGameRef} gameRef={gameRef} />
    </>
  )
}
