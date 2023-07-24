"use client"

// Import the functions you need from the SDKs you need
import { db } from "@/app/lib/firebase-client-initialization";
import { onSnapshot, doc, DocumentReference } from "firebase/firestore";
import { useEffect, useState } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import SignOutButton from "@/app/components/sign-out-button";
import SignInButton from "@/app/components/sign-in-button";
import CreateGameButton from "@/app/components/create-game-button";
import { Game, emptyGame, gameStates } from "@/app/types";
import Lobby from "@/app/components/lobby";
import GameList from "@/app/components/game-list";
import QuestionPanel from "@/app/components/question-panel";

export default function Home() {
  const [gameRef, setGameRef] = useState<DocumentReference>();
  const [game, setGame] = useState<Game>(emptyGame);
  const authUser = useFirebaseAuthentication();

  const showingQuestion = game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const currentQuestion = game.questions[game.currentQuestionIndex];

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
    if (!authUser.uid) {
      setGameRef(undefined);
    }
  }, [authUser.uid])

  return (
    <main className="p-24 flex justify-between container mx-auto">
      <div>
        {authUser.uid ? (<>
          {gameRef && (<>
            <div>
              Your Player Name: {game.players[authUser.uid]}
            </div>
            <div>
              Game ID: {gameRef.id}
            </div>
          </>)}
          {(game.state === gameStates.GAME_OVER) && <div>
            {gameStates.GAME_OVER}
          </div>}
          {(!gameRef || game.state === gameStates.GAME_OVER) && <div>
            <GameList setGameRef={setGameRef} />
            <CreateGameButton setGameRef={setGameRef} />
          </div>}
          {showingQuestion && gameRef && (<>
            <QuestionPanel game={game} gameRef={gameRef} currentQuestion={currentQuestion} />
          </>)}
          {game.state === gameStates.NOT_STARTED && gameRef && (<>
            <Lobby game={game} gameRef={gameRef} setGameRef={setGameRef} />
          </>)}
          <br />
          <SignOutButton />
        </>) : (<>
          <SignInButton />
        </>)}
      </div>
    </main>
  )
}
