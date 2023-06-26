"use client"

// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore, onSnapshot, doc, DocumentReference, updateDoc } from "firebase/firestore";
import { getAuth } from "firebase/auth";
import { useEffect, useState } from 'react';
import useFirebaseAuthentication from "./hooks/use-firebase-authentication";
import SignOutButton from "./components/sign-out-button";
import SignInButton from "./components/sign-in-button";
import CreateGameButton from "./components/create-game-button";
import { Game, emptyGame, gameStates } from "./types";
import Lobby from "./components/lobby";
import SubmitAnswerButton from "./components/submit-answer-button";
import RevealAnswersButton from "./components/reveal-answers-button";
import GameList from "./components/gameList";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBr0i2bC9kdsdRVh-9pQ5yFOjxpweiTJrQ",
  authDomain: "cloud-quiz-next.firebaseapp.com",
  projectId: "cloud-quiz-next",
  storageBucket: "cloud-quiz-next.appspot.com",
  messagingSenderId: "406096902405",
  appId: "1:406096902405:web:7311c44c3657568af1df6c",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

export default function Home() {
  const [answerSelection, setAnswerSelection] = useState<boolean[]>([]);
  const [gameRef, setGameRef] = useState<DocumentReference>();
  const [game, setGame] = useState<Game>(emptyGame);
  const authUser = useFirebaseAuthentication(auth);

  const showingQuestion = game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const currentQuestionIndex = game.currentQuestionIndex;
  const currentQuestion = game.questions[game.currentQuestionIndex];

  const onAnswerClick = (answerIndex: number): void => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
      // typescript gives an error for `.with` because it is a newer property
      // this can likely be removed once typescript is updated
      // @ts-expect-error
      setAnswerSelection(answerSelection.with(answerIndex, !answerSelection[answerIndex]));
    }
  }

  useEffect(() => {
    if (gameRef?.id) {
      const unsubscribe = onSnapshot(doc(db, "games", gameRef.id), (doc) => {
        const game = doc.data() as Game;
        setGame(game);
      });
      return unsubscribe;
    } else {
      setGame(emptyGame);
    }
  }, [gameRef])

  useEffect(() => {
    if (!authUser?.uid) {
      setGameRef(null);
    }
  }, [authUser?.uid])

  useEffect(() => {
    if (currentQuestion?.answers.length) {
      setAnswerSelection(Array(currentQuestion.answers.length).fill(false));
    }
  }, [game.currentQuestionIndex])

  const onNextQuestionClick = async () => {
    if (gameRef?.id) {
      if (game.currentQuestionIndex < Object.keys(game.questions).length - 1) {
        await updateDoc(gameRef, {
          currentQuestionIndex: game.currentQuestionIndex + 1,
          state: gameStates.AWAITING_PLAYER_ANSWERS,
        });
      } else {
        await updateDoc(gameRef, {
          state: gameStates.GAME_OVER,
        });
      }
    }
  }

  return (
    <main className="p-24 flex justify-between space-x-24">
      <div>
        {authUser ? (<>
          {(game.state === gameStates.GAME_OVER) && <div>
            {gameStates.GAME_OVER}
          </div>}
          {(!gameRef || game.state === gameStates.GAME_OVER) && <div>
            <CreateGameButton db={db} auth={auth} setGameRef={setGameRef} />
            <GameList auth={auth} db={db} setGameRef={setGameRef} />
          </div>}
          {game.state !== gameStates.NOT_STARTED && gameRef && (<>
            {showingQuestion && (<>
              <h2>
                {currentQuestion.prompt}
              </h2>
              {currentQuestion.answers.map((answer, index) => (<div className="flex pt-2" key={answer.text}>
                {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
                  <div>
                    {answer.isCorrect && '✅'}
                    {!answer.isCorrect && answerSelection[index] && '❌'}
                  </div>)}
                <button onClick={() => onAnswerClick(index)} className={`border ${answerSelection[index] ? 'text-blue-500' : 'text-inherit'}`}>
                  {answer.text}
                </button>
              </div>))}
            </>)
            }
            {game.state === gameStates.AWAITING_PLAYER_ANSWERS && (<>
              {answerSelection.some(selection => selection === true) ? (<>
                <SubmitAnswerButton auth={auth} gameRef={gameRef} currentQuestionIndex={currentQuestionIndex} answerSelection={answerSelection} />
              </>) : (<>
                <div className={`mt-20 text-gray-500`}>
                  Select an Answer
                </div>
              </>)}
              <RevealAnswersButton gameRef={gameRef} />
            </>)}
          </>)}
          {game.state === gameStates.NOT_STARTED && gameRef && (
            <Lobby auth={auth} gameRef={gameRef} setGameRef={setGameRef} />
          )}
          {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
            <button onClick={onNextQuestionClick} className={`border mt-20`}>
              Next Question
            </button>
          )}
          <br />
          <SignOutButton auth={auth} />
        </>) : (<>
          <SignInButton auth={auth} />
        </>)}
      </div>
    </main>
  )
}
