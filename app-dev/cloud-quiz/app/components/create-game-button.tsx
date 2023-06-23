"use client"
import { Auth } from "firebase/auth";
import { Firestore, QuerySnapshot, addDoc, collection, getDocs } from "firebase/firestore";
import { Game, Question, gameStates } from "../types";

export default function CreateGameButton({ db, auth, setGameRef }: { db: Firestore, auth: Auth, setGameRef: Function }) {
  const onCreateGameClick = async () => {
    const querySnapshot: QuerySnapshot = await getDocs(collection(db, "questions"));
    const questions = querySnapshot.docs.reduce((agg, doc, index) => {
      return { ...agg, [index]: doc.data() }
    }, {});
    if (!auth.currentUser) throw new Error('User must be signed in to start game');
    const leader = {
      displayName: auth.currentUser.displayName || '',
      uid: auth.currentUser.uid || '',
    };

    const gameRef = await addDoc(collection(db, "games"), {
      questions,
      leader,
      // TODO: Remove leader from game players, this just makes testing faster
      players: [leader],
      state: gameStates.NOT_STARTED,
      currentQuestionIndex: 0,
    });
    setGameRef(gameRef);
  }

  return (
    <button onClick={onCreateGameClick} className={`border mt-20`}>Create a New Game</button>
  )
}
