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

import {z} from 'zod';

export const GameIdSchema = z.string();

export const GameIdObjectSchema = z.object({gameId: GameIdSchema});

export const AnswerSelectionSchema = z.array(z.boolean());

export const AnswerSelectionWithGameIdSchema = z.object({
  gameId: GameIdSchema,
  answerSelection: AnswerSelectionSchema,
});

export const TimePerQuestionSchema = z.number({invalid_type_error: 'Time per question must be a number'}).int().max(600, 'Time per question must be 600 or less.').min(10, 'Time per question must be at least 10.');
export const TimePerAnswerSchema = z.number({invalid_type_error: 'Time per answer must be a number'}).int().max(600, 'Time per answer must be 600 or less.').min(5, 'Time per answer must be at least 5.');


export const questionAdvancementOptionDetails = [
  {
    type: 'MANUAL',
    description: 'Manually advance to the next question.',
    shortName: 'Manual',
    automaticallyAdvanceToNextQuestion: false,
  },
  {
    type: 'AUTOMATIC',
    description: 'Automatically advance question on a timer.',
    shortName: 'Automatic',
    automaticallyAdvanceToNextQuestion: true,
  },
] as const;
const questionAdvancementOptions = ['MANUAL', 'AUTOMATIC'] as const;
export const QuestionAdvancementEnum = z.enum(questionAdvancementOptions);
export const questionAdvancements = QuestionAdvancementEnum.Values;
export type QuestionAdvancement = z.infer<typeof QuestionAdvancementEnum>;

export const GameSettingsSchema = z.object({
  timePerQuestion: TimePerQuestionSchema,
  timePerAnswer: TimePerAnswerSchema,
  questionAdvancement: QuestionAdvancementEnum,
});
export type GameSettings = z.infer<typeof GameSettingsSchema>;

const AnswerSchema = z.object({
  isCorrect: z.boolean(),
  isSelected: z.boolean().default(false),
  text: z.string(),
});

export const QuestionSchema = z.object({
  answers: z.array(AnswerSchema).min(1).max(4),
  prompt: z.string(),
  explanation: z.string(),
  playerGuesses: z.record(z.string(), z.array(z.boolean())).default({}),
});
export type Question = z.infer<typeof QuestionSchema>;

const gameStatesOptions = ['NOT_STARTED', 'SHOWING_CORRECT_ANSWERS', 'AWAITING_PLAYER_ANSWERS', 'GAME_OVER'] as const;
const GameStateEnum = z.enum(gameStatesOptions);
export const gameStates = GameStateEnum.Values;

export const GameStateUpdateSchema = z.object({
  state: GameStateEnum,
  currentQuestionIndex: z.number().int().nonnegative(),
});
export type GameStateUpdate = z.infer<typeof GameStateUpdateSchema>;

export const LeaderSchema = z.object({
  uid: z.string(),
  displayName: z.string(),
});
const emptyLeader = LeaderSchema.parse({
  uid: '',
  displayName: '',
});

export const GameSchema = z.object({
  questions: z.record(z.string(), QuestionSchema),
  leader: LeaderSchema,
  players: z.record(z.string(), z.string()),
  state: GameStateEnum,
  currentQuestionIndex: z.number().int().nonnegative(),
  currentStateStartTime: z.object({seconds: z.number()}),
  questionAdvancement: QuestionAdvancementEnum,
  timePerQuestion: TimePerQuestionSchema,
  timePerAnswer: TimePerAnswerSchema,
});
export const emptyGame = GameSchema.parse({
  questions: {},
  leader: emptyLeader,
  players: {},
  state: 'NOT_STARTED',
  currentQuestionIndex: 0,
  questionAdvancement: 'AUTOMATIC',
  currentStateStartTime: {seconds: 0},
  timePerQuestion: 60,
  timePerAnswer: 20,
});
export type Game = z.infer<typeof GameSchema>;

export const TokensSchema = z.object({
  userToken: z.string(),
  appCheckToken: z.string(),
});
export type Tokens = z.infer<typeof TokensSchema>;
