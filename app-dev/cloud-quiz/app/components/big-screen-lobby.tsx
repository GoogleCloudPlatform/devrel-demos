"use client"

import { DocumentReference } from "firebase/firestore";
import StartGameButton from "@/app/components/start-game-button";
import DeleteGameButton from "@/app/components/delete-game-button";
import PlayerList from "./player-list";
import { Game } from "@/app/types";
import useFirebaseAuthentication from "../hooks/use-firebase-authentication";
import QRCode from "react-qr-code";

export default function PlayerLobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {

  const authUser = useFirebaseAuthentication();

  return (
    <div className="grid grid-cols-2">
      {authUser.uid === game.leader.uid ? (<>
        <div>
          <PlayerList game={game} />
        </div>
        <div>
          <StartGameButton gameRef={gameRef} />
          <div>
            Scan this QR code to join the game:
            <QRCode value={`${location.protocol}//${window.location.host}/game/${gameRef.id}`} />
          </div>
          <DeleteGameButton gameRef={gameRef} />
        </div>
      </>) : (<>
        <PlayerList game={game} />
      </>)}
    </div>
  )
}
