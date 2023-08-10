export type Answer = {
  isCorrect: boolean;
  isSelected: boolean;
  text: string;
}

export type Question = {
  answers: Array<Answer>;
  prompt: string;
  playerGuesses?: any;
}

export const emptyQuestion: Question = {
  answers: [],
  prompt: ''
};

export const gameStates = {
  NOT_STARTED: 'NOT_STARTED',
  SHOWING_CORRECT_ANSWERS: 'SHOWING_CORRECT_ANSWERS',
  AWAITING_PLAYER_ANSWERS: 'AWAITING_PLAYER_ANSWERS',
  GAME_OVER: 'GAME_OVER',
} as const;

export type GameState = (typeof gameStates)[keyof typeof gameStates];

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
  players: {
    [key: string]: string;
  };
  state: GameState;
  currentQuestionIndex: number;
  startTime: any;
  timePerQuestion: number;
  timePerAnswer: number;
}

export const emptyGame: Game = {
  questions: [],
  leader: emptyPlayer,
  players: {},
  state: gameStates.NOT_STARTED,
  currentQuestionIndex: -1,
  startTime: '',
  timePerQuestion: -1,
  timePerAnswer: -1,
};

export type RouteWithCurrentStatus = {
  name: string;
  href: string;
  current: boolean;
}
