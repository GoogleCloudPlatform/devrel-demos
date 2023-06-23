"use client"

// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore, collection, getDocs, DocumentSnapshot, QuerySnapshot } from "firebase/firestore";
import { useEffect, useState } from 'react';
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

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

type Answer = {
  isCorrect: boolean;
  isSelected: boolean;
  text: string;
}

type Question = {
  answers: Array<Answer>;
  prompt: string;
}

type GameState = 'NO_ANSWER_SUBMITTED' | 'ANSWER_SUBMITTED';

export default function Home() {
  const [questions, setQuestions] = useState<Array<Question>>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [currentQuestion, setCurrentQuestion] = useState<Question>({ answers: [], prompt: '' });
  const [gameState, setGameState] = useState<GameState>('NO_ANSWER_SUBMITTED');

  useEffect(() => {
    const getQuestions = async () => {
      const querySnapshot: QuerySnapshot = await getDocs(collection(db, "questions"));
      const questions = querySnapshot.docs.map((doc) => {
        return doc.data() as Question;
      });
      setQuestions(questions);
      if (currentQuestion?.prompt === '') {
        setCurrentQuestion(questions[currentQuestionIndex]);
      }
    }
    getQuestions();
  }, [])

  const onAnswerClick = (answerIndex: number, answer: Answer): void => {
    setCurrentQuestion({
      ...currentQuestion,
      // typescript gives an error for `.with` because it is a newer property
      // this can likely be removed once typescript is updated
      // @ts-expect-error
      answers: currentQuestion.answers.with(answerIndex, {
        ...answer,
        isSelected: !answer.isSelected,
      }),
    })
  }

  const onSubmitAnswerClick = (): void => {
    setGameState('ANSWER_SUBMITTED');
  }

  const onNextQuestionClick = (): void => {
    setGameState('NO_ANSWER_SUBMITTED');
    const newQuestionIndex = (currentQuestionIndex + 1) % questions.length;
    setCurrentQuestion(questions[newQuestionIndex]);
    setCurrentQuestionIndex(newQuestionIndex);
  }

  return (
    <main className="p-24">
      <h2>
        {currentQuestion.prompt}
      </h2>
      {currentQuestion.answers.map((answer, index) => (<div className="flex pt-2" key={answer.text}>
        {gameState === 'ANSWER_SUBMITTED' && (<div>
          { answer.isCorrect && '✅' }
          { !answer.isCorrect && answer.isSelected && '❌' }
        </div>)}
        <button onClick={() => onAnswerClick(index, answer)} className={`border ${answer.isSelected ? 'text-blue-500' : 'text-inherit'}`}>
          {answer.text}
        </button>
      </div>))}
      {gameState === 'NO_ANSWER_SUBMITTED' && (currentQuestion.answers.every((answer) => !answer.isSelected) ? (<>
        <div className={`mt-20 text-gray-500`}>
          Select an Answer
        </div>
      </>) : (<>
        <button onClick={onSubmitAnswerClick} className={`border mt-20`}>
          Submit Your Answer
        </button>
      </>)
      )}
      {gameState === 'ANSWER_SUBMITTED' && (
        <button onClick={onNextQuestionClick} className={`border mt-20`}>
          Next Question
        </button>
      )}
    </main>
  )
}
