"use client"

import { DocumentData, DocumentReference } from "firebase/firestore";
import StartGameButton from "@/app/components/start-game-button";
import DeleteGameButton from "@/app/components/delete-game-button";
import ExitGameButton from "@/app/components/exit-game-button";
import { Dispatch, SetStateAction } from "react";
import PlayerList from "./player-list";
import { Game } from "@/app/types";
import useFirebaseAuthentication from "../hooks/use-firebase-authentication";
import QRCode from "react-qr-code";

export default function Lobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {

  const authUser = useFirebaseAuthentication();

  return (
    <>
      <PlayerList game={game} />
      {authUser.uid === game.leader.uid && <StartGameButton gameRef={gameRef} />}
      {authUser.uid === game.leader.uid ? <DeleteGameButton gameRef={gameRef} /> : <ExitGameButton gameRef={gameRef} />}
      <QRCode value={window.location.href} />
    </>
  )
}
