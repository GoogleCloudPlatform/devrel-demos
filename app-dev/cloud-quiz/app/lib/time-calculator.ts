import { Game, gameStates } from "@/app/types";

export const timeCalculator = ({currentTimeInSeconds, game}: {currentTimeInSeconds: number, game: Game}) => {
  const timeElapsed = currentTimeInSeconds - game.startTime.seconds;
  const timePerQuestionAndAnswer = game.timePerQuestion + 0.5 + game.timePerAnswer;
  const timeToShowCurrentQuestionAnswer = timePerQuestionAndAnswer * (game.currentQuestionIndex) + game.timePerQuestion + 0.5;
  const timeToStartNextQuestion = timePerQuestionAndAnswer * (game.currentQuestionIndex + 1);
  const isTimeToShowAnswer = timeElapsed > timeToShowCurrentQuestionAnswer && game.state === gameStates.AWAITING_PLAYER_ANSWERS;
  const isTimeToStartNextQuestion = timeElapsed > timeToStartNextQuestion;
  const isOverTime = isTimeToShowAnswer || isTimeToStartNextQuestion;

  const isAFullThreeSecondsAfterTimeToShowAnswer = timeElapsed > timeToShowCurrentQuestionAnswer + 3 && game.state === gameStates.AWAITING_PLAYER_ANSWERS;
  const isAFullThreeSecondsAfterTimeToStartNextQuestion = timeElapsed > timeToStartNextQuestion + 3;
  const isAFullThreeSecondsOverTime = isAFullThreeSecondsAfterTimeToShowAnswer || isAFullThreeSecondsAfterTimeToStartNextQuestion;

  return {
    timeElapsed,
    timePerQuestionAndAnswer,
    timeToShowCurrentQuestionAnswer,
    timeToStartNextQuestion,
    isTimeToShowAnswer,
    isTimeToStartNextQuestion,
    isOverTime,
    isAFullThreeSecondsOverTime,
  }
}
