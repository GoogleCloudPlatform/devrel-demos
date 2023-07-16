"use client"

import { DocumentReference, serverTimestamp, updateDoc } from "firebase/firestore";
import { gameStates } from "@/app/types";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

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
    <button onClick={() => onStartGameClick(gameRef)} className={`border mt-20`}>
      Start Game
    </button>
  )
}
