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

import { Game, gameStates } from "@/app/types";

export const timeCalculator = ({ currentTimeInMillis, game }: { currentTimeInMillis: number, game: Game }) => {
  // all times are in seconds unless noted as `InMillis`
  const timeElapsedInMillis = currentTimeInMillis - game.startTime.seconds * 1000;
  const timeElapsed = timeElapsedInMillis / 1000;
  const timePerQuestionAndAnswer = game.timePerQuestion + game.timePerAnswer;
  const timeToShowCurrentQuestionAnswer = timePerQuestionAndAnswer * (game.currentQuestionIndex) + game.timePerQuestion;
  const timeToStartNextQuestion = timePerQuestionAndAnswer * (game.currentQuestionIndex + 1);
  const isTimeToShowAnswer = timeElapsed > timeToShowCurrentQuestionAnswer && game.state === gameStates.AWAITING_PLAYER_ANSWERS;
  const isTimeToStartNextQuestion = timeElapsed > timeToStartNextQuestion;
  const isOverTime = isTimeToShowAnswer || isTimeToStartNextQuestion;

  let timeLeft;
  let countDirection: "up" | "down";
  let timeToCountDown;

  if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
    timeLeft = timeToShowCurrentQuestionAnswer - timeElapsed;
    countDirection = "down";
    timeToCountDown = game.timePerQuestion;
  } else {
    timeLeft = timeToStartNextQuestion - timeElapsed;
    countDirection = "up";
    timeToCountDown = game.timePerAnswer;
  }

  const displayTime = Math.max(Math.floor(timeLeft), 0);

  return {
    timeElapsed,
    displayTime,
    timeLeft,
    timeToCountDown,
    countDirection,
    timePerQuestionAndAnswer,
    timeToShowCurrentQuestionAnswer,
    timeToStartNextQuestion,
    isTimeToShowAnswer,
    isTimeToStartNextQuestion,
    isOverTime,
  }
}
