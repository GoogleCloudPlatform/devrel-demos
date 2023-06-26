"use client"

import { DocumentData, DocumentReference, deleteField, updateDoc } from "firebase/firestore";
import { Dispatch, SetStateAction } from "react";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function ExitGameButton({ setGameRef, gameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>>, gameRef: DocumentReference }) {
  const authUser = useFirebaseAuthentication();
  const onExitGameClick = async (gameRef: DocumentReference) => {
    if (!authUser) throw new Error('User must be signed in to exit game');

    await updateDoc(gameRef, {
      [`players.${authUser.uid}`]: deleteField(),
    });

    setGameRef(undefined);
  }

  return (
    <div>
      <button onClick={() => onExitGameClick(gameRef)} className={`border mt-20`}>Exit Game</button>
    </div>
  )
}
