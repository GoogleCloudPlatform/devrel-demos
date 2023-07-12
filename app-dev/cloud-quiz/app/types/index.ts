import { FieldValue, Timestamp, serverTimestamp } from "firebase/firestore";

export type Answer = {
  isCorrect: boolean;
  isSelected: boolean;
  text: string;
}

export type Question = {
  answers: Array<Answer>;
  prompt: string;
}

export const emptyQuestion: Question = {
  answers: [],
  prompt: ''
};

export type GameState = 'NOT_STARTED' | 'NO_ANSWER_SUBMITTED' | 'ANSWER_SUBMITTED' | 'SHOWING_CORRECT_ANSWERS' | 'AWAITING_PLAYER_ANSWERS' | 'GAME_OVER';

export const gameStates = {
  NOT_STARTED: 'NOT_STARTED',
  NO_ANSWER_SUBMITTED: 'NO_ANSWER_SUBMITTED',
  ANSWER_SUBMITTED: 'ANSWER_SUBMITTED',
  SHOWING_CORRECT_ANSWERS: 'SHOWING_CORRECT_ANSWERS',
  AWAITING_PLAYER_ANSWERS: 'AWAITING_PLAYER_ANSWERS',
  GAME_OVER: 'GAME_OVER',
} as const;

export type Player = {
  uid: string;
  displayName: string;
}

export const emptyPlayer: Player = {
  uid: '',
  displayName: '',
}

export type Game = {
  questions: Array<Question>;
  leader: Player,
  players: Player[];
  state: GameState;
  currentQuestionIndex: number;
  startTime: any;
  timePerQuestion: number;
  timePerAnswer: number;
}

export const emptyGame: Game = {
  questions: [],
  leader: emptyPlayer,
  players: [],
  state: gameStates.NOT_STARTED,
  currentQuestionIndex: -1,
  startTime: '',
  timePerQuestion: -1,
  timePerAnswer: -1,
};
