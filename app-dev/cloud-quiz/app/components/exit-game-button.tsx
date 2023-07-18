"use client"

import { DocumentData, DocumentReference } from "firebase/firestore";
import { Dispatch, SetStateAction } from "react";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function ExitGameButton({ setGameRef, gameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>>, gameRef: DocumentReference }) {
  const authUser = useFirebaseAuthentication();

  const onExitGameClick = async (gameRef: DocumentReference) => {
    const token = await authUser.getIdToken();
    await fetch('/api/exit-game', {
      method: 'POST',
      body: JSON.stringify({ gameId: gameRef.id }),
      headers: {
        Authorization: token,
      }
    }).then(() => setGameRef(undefined))
    .catch(error => {
      console.error({ error })
    });
  }

  return (
    <div>
      <button onClick={() => onExitGameClick(gameRef)} className={`border mt-20`}>Exit Game</button>
    </div>
  )
}
