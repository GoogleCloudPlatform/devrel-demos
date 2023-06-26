"use client"

import { auth } from "@/app/lib/firebase-initialization";
import { DocumentData, DocumentReference, deleteField, updateDoc } from "firebase/firestore";
import { Dispatch, SetStateAction } from "react";

export default function ExitGameButton({ setGameRef, gameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>>, gameRef: DocumentReference }) {

  const onExitGameClick = async (gameRef: DocumentReference) => {
    if (!auth.currentUser) throw new Error('User must be signed in to start game');

    await updateDoc(gameRef, {
      [`players.${auth.currentUser.uid}`]: deleteField(),
    });

    setGameRef(undefined);
  }


  return (
    <div>
      <button onClick={() => onExitGameClick(gameRef)} className={`border mt-20`}>Exit Game</button>
    </div>
  )
}
