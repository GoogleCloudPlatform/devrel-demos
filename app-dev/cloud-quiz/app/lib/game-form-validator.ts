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

import { Game } from "@/app/types";

export const gameFormValidator = ({timePerQuestion, timePerAnswer}: Partial<Game>): string => {
  if (!timePerQuestion) return 'Must specify the time per question.';
  if (!timePerAnswer) return 'Must specify the time per answer.';
  if (timePerQuestion < 10) return 'Time per question must be at least 10.';
  if (timePerAnswer < 5) return 'Time per answer must be at least 5.';
  if (timePerQuestion > 600) 'Time per question must be 600 or less.';
  if (timePerAnswer > 600) return 'Time per answer must be 600 or less.';
  return '';
}