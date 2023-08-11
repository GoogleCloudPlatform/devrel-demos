"use client"

import { DocumentReference } from "firebase/firestore";
import ExitGameButton from "@/app/components/exit-game-button";
import PlayerList from "@/app/components/player-list";
import { Game } from "@/app/types";
import ShareLinkPanel from "@/app/components/share-link-panel";
import { useState } from "react";

export default function PlayerLobby({ game, gameRef }: { game: Game; gameRef: DocumentReference }) {

  const [showSharePanel, setShowSharePanel] = useState<Boolean>(false);

  return (
    <>
      {/* <ExitGameButton gameRef={gameRef} /> */}

      <center>
        {showSharePanel ? (
          <>
            <button onClick={() => setShowSharePanel(false)} className={`border m-2 mt-10 p-2`}>Hide Share Panel</button>
            <ShareLinkPanel gameRef={gameRef} />
          </>
        ) : (<button onClick={() => setShowSharePanel(true)} className={`border m-10 p-2`}>Invite Others to Join</button>)}
        <PlayerList game={game} />
      </center>
    </>
  )
}
