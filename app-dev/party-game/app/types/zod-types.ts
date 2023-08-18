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

const gameId = z.string();

export const GameIdObject = z.object({gameId});

export const AnswerSelection = z.array(z.boolean());

export const AnswerSelectionWithGameId = z.object({
  gameId,
  answerSelection: AnswerSelection,
});

export const GameSettings = z.object({
  timePerQuestion: z.number({invalid_type_error: 'Time per question must be a number'}).int().max(600, 'Time per question must be 600 or less.').min(10, 'Time per question must be at least 10.'),
  timePerAnswer: z.number({invalid_type_error: 'Time per answer must be a number'}).int().max(600, 'Time per answer must be 600 or less.').min(5, 'Time per answer must be at least 5.'),
});
