"use client"

import { DocumentReference } from "firebase/firestore";
import { Game, Question, gameStates } from "@/app/types";
import BorderCountdownTimer from "@/app/components/border-countdown-timer";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import Image from 'next/image';
import QRCode from "react-qr-code";
import { usePathname } from "next/navigation";

export default function QuestionPanel({ game, gameRef, currentQuestion }: { game: Game, gameRef: DocumentReference, currentQuestion: Question }) {
  const authUser = useFirebaseAuthentication();
  const pathname = usePathname();
  const isBigScreen = pathname.includes('/big-screen');

  const existingGuesses = currentQuestion?.playerGuesses && currentQuestion.playerGuesses[authUser.uid];
  const answerSelection = existingGuesses || Array(currentQuestion.answers.length).fill(false);

  const onAnswerClick = async (answerIndex: number) => {
    if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
      const newAnswerSelection = answerSelection.with(answerIndex, !answerSelection[answerIndex]);
      const token = await authUser.getIdToken();
      await fetch('/api/update-answer', {
        method: 'POST',
        body: JSON.stringify({ newAnswerSelection, gameId: gameRef.id }),
        headers: {
          Authorization: token,
        }
      })
        .catch(error => {
          console.error({ error })
        });
    }
  }

  const gameShareLink = `${location.protocol}//${location.host}/game/${gameRef.id}`;

  return (
    <div className={`grid ${isBigScreen ? 'grid-cols-2' : 'lg:grid-cols-2'}`}>
      <div className="flex flex-col">
        <BorderCountdownTimer game={game}>
          <h2 className="text-2xl font-light">
            {currentQuestion.prompt}
          </h2>
        </BorderCountdownTimer>
        <center className={`hidden bg-gray-100 p-10 h-[50vh] lg:block`}>
          {isBigScreen ? (<>
            <div>
              Just getting here?
            </div>
            <div>
              Scan the QR Code to join the game!
            </div>
            <QRCode value={gameShareLink} />
          </>) : (<>
            <center className='pt-20'>
              <div className='h-20'>
                <Image
                  src='/google-cloud-logo.svg'
                  alt='Google Cloud Logo'
                  width={0}
                  height={0}
                  sizes="100vw"
                  style={{ width: '100%', height: '100%' }} // optional            
                />
              </div>
              <h1 className='text-4xl pt-10'>Cloud Quiz</h1>
            </center>
          </>)}
        </center>
      </div>
      <div className="grid grid-cols-2 h-[50vh] lg:h-full">
        {currentQuestion.answers.map((answer, index) => (<div className="flex" key={answer.text}>
          <button onClick={() => onAnswerClick(index)}
            className=
            {`border-8 m-2 w-full
                ${answerSelection[index] ? 'text-[var(--google-cloud-blue)]' : 'text-inherit'}
                ${answerSelection[index] && game.state !== gameStates.SHOWING_CORRECT_ANSWERS ? 'border-[var(--google-cloud-blue)]' : ''}
                ${answerSelection[index] && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-[var(--google-cloud-green)]'}
                ${answerSelection[index] && !answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-[var(--google-cloud-red)]'}
                ${!answerSelection[index] && answer.isCorrect && game.state === gameStates.SHOWING_CORRECT_ANSWERS && 'border-[var(--google-cloud-green)] border-dotted'}`}>
            {answer.text}
            {game.state === gameStates.SHOWING_CORRECT_ANSWERS && (
              <div>
                {answer.isCorrect && '✅'}
                {!answer.isCorrect && answerSelection[index] && '❌'}
              </div>)}
          </button>
        </div>))}
      </div>
    </div>
  )
}
