"use client"

import { Auth } from "firebase/auth"
import { DocumentReference, deleteField, updateDoc } from "firebase/firestore";

export default function ExitGameButton({ auth, setGameRef, gameRef }: { auth: Auth, setGameRef: Function, gameRef: DocumentReference }) {

  const onExitGameClick = async (gameRef: DocumentReference) => {
    if (!auth.currentUser) throw new Error('User must be signed in to start game');

    await updateDoc(gameRef, {
      [`players.${auth.currentUser.uid}`]: deleteField(),
    });

    setGameRef(null);
  }


  return (
    <div>
      <button onClick={() => onExitGameClick(gameRef)} className={`border mt-20`}>Exit Game</button>
    </div>
  )
}
