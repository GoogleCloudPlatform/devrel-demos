/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export type Answer = {
  isCorrect: boolean;
  isSelected: boolean;
  text: string;
}

export type Question = {
  answers: Array<Answer>;
  prompt: string;
  explanation: string;
  playerGuesses: {
    [key: string]: Boolean[];
  };
}

export const emptyQuestion: Question = {
  answers: [],
  prompt: '',
  explanation: '',
  playerGuesses: {},
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
