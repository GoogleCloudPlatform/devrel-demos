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
