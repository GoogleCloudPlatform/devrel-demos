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

const GameIdSchema = z.string();

export const GameIdObjectSchema = z.object({gameId: GameIdSchema});

export const AnswerSelectionSchema = z.array(z.boolean());

export const AnswerSelectionWithGameIdSchema = z.object({
  gameId: GameIdSchema,
  answerSelection: AnswerSelectionSchema,
});

const TimePerQuestionSchema = z.number({invalid_type_error: 'Time per question must be a number'}).int().max(600, 'Time per question must be 600 or less.').min(10, 'Time per question must be at least 10.');
const TimePerAnswerSchema = z.number({invalid_type_error: 'Time per answer must be a number'}).int().max(600, 'Time per answer must be 600 or less.').min(5, 'Time per answer must be at least 5.');

export const GameSettingsSchema = z.object({timePerQuestion: TimePerQuestionSchema, timePerAnswer: TimePerAnswerSchema});

const AnswerSchema = z.object({
  isCorrect: z.boolean(),
  isSelected: z.boolean().default(false),
  text: z.string(),
});
export type Answer = z.infer<typeof AnswerSchema>;

export const QuestionSchema = z.object({
  answers: z.array(AnswerSchema).default([]),
  prompt: z.string().default(''),
  explanation: z.string().default(''),
  playerGuesses: z.record(z.string(), z.array(z.boolean())).default({}),
});
export const emptyQuestion = QuestionSchema.parse({});
export type Question = z.infer<typeof QuestionSchema>;

const gameStatesOptions = ['NOT_STARTED', 'SHOWING_CORRECT_ANSWERS', 'AWAITING_PLAYER_ANSWERS', 'GAME_OVER'] as const;
const GameStateEnum = z.enum(gameStatesOptions);
export const gameStates = GameStateEnum.Values;

export const LeaderSchema = z.object({
  uid: z.string().default(''),
  displayName: z.string().default(''),
});
const emptyLeader = LeaderSchema.parse({});

export const GameSchema = z.object({
  questions: z.record(z.string(), QuestionSchema).default({}),
  leader: LeaderSchema.default(emptyLeader),
  players: z.record(z.string(), z.string()).default({}),
  state: GameStateEnum.default(gameStates.NOT_STARTED),
  currentQuestionIndex: z.number().int().nonnegative().default(0),
  startTime: z.object({seconds: z.number()}).default({seconds: -1}),
  timePerQuestion: TimePerQuestionSchema.default(60),
  timePerAnswer: TimePerAnswerSchema.default(20),
});
export type Game = z.infer<typeof GameSchema>;
export const emptyGame = GameSchema.parse({});

const RouteWithCurrentStatusSchema = z.object({
  name: z.string(),
  href: z.string(),
  current: z.string(),
});
export type RouteWithCurrentStatus = z.infer<typeof RouteWithCurrentStatusSchema>;
