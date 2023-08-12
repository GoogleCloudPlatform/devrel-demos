import { Game, gameStates } from "@/app/types";

export const timeCalculator = ({ currentTimeInMillis, game }: { currentTimeInMillis: number, game: Game }) => {
  const timeElapsed = currentTimeInMillis - game.startTime.seconds * 1000;
  const timePerQuestionAndAnswer = game.timePerQuestion + 0.5 + game.timePerAnswer;
  const timeToShowCurrentQuestionAnswer = timePerQuestionAndAnswer * (game.currentQuestionIndex) + game.timePerQuestion + 0.5;
  const timeToStartNextQuestion = timePerQuestionAndAnswer * (game.currentQuestionIndex + 1);
  const isTimeToShowAnswer = timeElapsed > timeToShowCurrentQuestionAnswer && game.state === gameStates.AWAITING_PLAYER_ANSWERS;
  const isTimeToStartNextQuestion = timeElapsed > timeToStartNextQuestion;
  const isOverTime = isTimeToShowAnswer || isTimeToStartNextQuestion;

  let timeLeft;
  let countDirection: "up" | "down";
  let timeToCountDown;

  if (game.state === gameStates.AWAITING_PLAYER_ANSWERS) {
    timeLeft = timeToShowCurrentQuestionAnswer - timeElapsed / 1000;
    countDirection = "down";
    timeToCountDown = game.timePerQuestion;
  } else {
    timeLeft = timeToStartNextQuestion - timeElapsed / 1000;
    countDirection = "up";
    timeToCountDown = game.timePerAnswer;
  }

  const displayTime = Math.max(Math.floor(timeLeft), 0);

  const isAFullThreeSecondsAfterTimeToShowAnswer = timeElapsed > timeToShowCurrentQuestionAnswer + 3 && game.state === gameStates.AWAITING_PLAYER_ANSWERS;
  const isAFullThreeSecondsAfterTimeToStartNextQuestion = timeElapsed > timeToStartNextQuestion + 3;
  const isAFullThreeSecondsOverTime = isAFullThreeSecondsAfterTimeToShowAnswer || isAFullThreeSecondsAfterTimeToStartNextQuestion;

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
    isAFullThreeSecondsOverTime,
  }
}
