"use client"

import { DocumentReference } from "firebase/firestore";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import "./start-game-button.css";

export default function StartGameButton({gameRef}: {gameRef: DocumentReference}) {
  const authUser = useFirebaseAuthentication();
  const onStartGameClick = async (gameRef: DocumentReference) => {
    const token = await authUser.getIdToken();
    await fetch('/api/start-game', {
      method: 'POST',
      body: JSON.stringify({ gameId: gameRef.id }),
      headers: {
        Authorization: token,
      }
    })
    .catch(error => {
      console.error({ error })
    });
  }

  return (
    <button onClick={() => onStartGameClick(gameRef)} className={`start draw`}>
      Start Game Now ►
    </button>
  )
}
