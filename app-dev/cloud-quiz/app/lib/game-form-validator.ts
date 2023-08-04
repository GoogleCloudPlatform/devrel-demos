import { Game } from "@/app/types";

export const gameFormValidator = ({timePerQuestion, timePerAnswer}: Partial<Game>): string => {
  if (!timePerQuestion) return 'Must specify the time per question.';
  if (!timePerAnswer) return 'Must specify the time per answer.';
  if (timePerQuestion < 1) 'Time per question must be at least 1.';
  if (timePerAnswer < 1) return 'Time per answer must be at least 1.';
  if (timePerQuestion > 600) 'Time per question must be 600 or less.';
  if (timePerAnswer > 600) return 'Time per answer must be 600 or less.';
  return '';
}