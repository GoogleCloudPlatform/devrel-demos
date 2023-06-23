"use client"
import { Auth } from "firebase/auth";
import { Firestore, QuerySnapshot, addDoc, collection, getDocs } from "firebase/firestore";

type Answer = {
  isCorrect: boolean;
  isSelected: boolean;
  text: string;
}

type Question = {
  answers: Array<Answer>;
  prompt: string;
}

type GameState = 'NOT_STARTED' | 'NO_ANSWER_SUBMITTED' | 'ANSWER_SUBMITTED';

type Game = {
  questions: Array<Question>;
  leader: string;
  players: string[];
  state: GameState;
}

export default function CreateGameButton({ db, auth, setGameRef }: { db: Firestore, auth: Auth, setGameRef: Function }) {
  const onCreateGameClick = async () => {
    const querySnapshot: QuerySnapshot = await getDocs(collection(db, "questions"));
    const questions = querySnapshot.docs.map((doc) => {
      return doc.data() as Question;
    });
    if (!auth.currentUser) throw new Error('User must be signed in to start game');
    const leader = {
      displayName: auth.currentUser.displayName,
      uid: auth.currentUser.uid,
    };
    const gameRef = await addDoc(collection(db, "games"), {
      questions,
      leader,
      // TODO: Remove leader from game players, this just makes testing faster
      players: [leader],
    });
    setGameRef(gameRef);
  }

  return (
    <button onClick={onCreateGameClick}>Create a New Game</button>
  )
}
