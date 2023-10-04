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

'use client';

import {useRouter} from 'next/navigation';
import {useEffect, useState} from 'react';
import BigColorBorderButton from './big-color-border-button';
import {QuestionAdvancement, QuestionAdvancementEnum, TimePerAnswerSchema, TimePerQuestionSchema, questionAdvancements} from '@/app/types';
import {createGameAction} from '@/app/actions/create-game';
import {z} from 'zod';
import {getTokens} from '@/app/lib/client-token-generator';

const {MANUAL, AUTOMATIC} = questionAdvancements;
const defaultTimePerQuestion = 60;
const defaultTimePerAnswer = 20;

export default function CreateGameForm() {
  const [questionAdvancement, setQuestionAdvancement] = useState<QuestionAdvancement>(MANUAL);
  const [timePerQuestionInputValue, setTimePerQuestionInputValue] = useState<string>(defaultTimePerQuestion.toString());
  const [timePerAnswerInputValue, setTimePerAnswerInputValue] = useState<string>(defaultTimePerAnswer.toString());
  const timePerQuestion = timePerQuestionInputValue ? parseInt(timePerQuestionInputValue) : -0.5;
  const timePerAnswer = timePerAnswerInputValue ? parseInt(timePerAnswerInputValue) : -0.5;
  const [timePerQuestionError, setTimePerQuestionError] = useState<string>('');
  const [timePerAnswerError, setTimePerAnswerError] = useState<string>('');
  const [submissionErrorMessage, setSubmissionErrorMessage] = useState<string>('');
  const router = useRouter();
  const onCreateGameSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const gameSettings = {timePerQuestion, timePerAnswer, questionAdvancement};
      const tokens = await getTokens();
      const response = await createGameAction({gameSettings, tokens});
      router.push(`/game/${response.gameId}`);
    } catch (error) {
      setSubmissionErrorMessage('There was an error handling the request.');
    }
  };

  useEffect(() => {
    setSubmissionErrorMessage('');
  }, [timePerQuestion, timePerAnswer]);

  useEffect(() => {
    try {
      TimePerQuestionSchema.parse(timePerQuestion);
      setTimePerQuestionError('');
    } catch (error) {
      if (error instanceof z.ZodError) {
        setTimePerQuestionError(error.issues[0].message);
      }
    }
  }, [timePerQuestion]);

  useEffect(() => {
    try {
      TimePerAnswerSchema.parse(timePerAnswer);
      setTimePerAnswerError('');
    } catch (error) {
      if (error instanceof z.ZodError) {
        setTimePerAnswerError(error.issues[0].message);
      }
    }
  }, [timePerAnswer]);

  return (
    <div className="w-full max-w-lg mx-auto border-8 border-r-[var(--google-cloud-blue)] border-t-[var(--google-cloud-red)] border-b-[var(--google-cloud-green)] border-l-[var(--google-cloud-yellow)]">
      <form className="bg-white px-8 py-12" onSubmit={onCreateGameSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-bold mb-2" htmlFor="timePerQuestion">
            Time (in seconds) to answer the question
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline"
            id="timePerQuestion"
            type="text"
            inputMode="numeric"
            value={timePerQuestionInputValue}
            onChange={(event) => setTimePerQuestionInputValue(event.target.value)}
            placeholder={defaultTimePerQuestion.toString()}
          />
          <p className="text-red-500 text-xs italic">{timePerQuestionError ? timePerQuestionError : <>&nbsp;</>}</p>
        </div>
        <div className="mb-6">
          <label className="block text-sm font-bold mb-2" htmlFor="questionAdvancement">
            Advancement to the next question
          </label>
          <select
          // shadow appearance-none border rounded w-full py-2 px-3 mb-3 leading-tight focus:outline-none focus:shadow-outline
            className="shadow border rounded w-full py-2 px-3 mb-3 leading-tight focus:outline-none focus:shadow-outline"
            value={questionAdvancement}
            onChange={(event) => {
              setQuestionAdvancement(QuestionAdvancementEnum.parse(event.target.value));
            }}
          >
            <option value={MANUAL}>Manually</option>
            <option value={AUTOMATIC}>Automatically on a timer</option>
          </select>
        </div>
        {questionAdvancement === AUTOMATIC && (<>
          <div className="mb-6">
            <label className="block text-sm font-bold mb-2" htmlFor="timePerAnswer">
              Time (in seconds) to review the answers
            </label>
            <input
              className="shadow appearance-none border rounded w-full py-2 px-3 mb-3 leading-tight focus:outline-none focus:shadow-outline"
              id="timePerAnswer"
              type="text"
              inputMode="numeric"
              value={timePerAnswerInputValue}
              onChange={(event) => setTimePerAnswerInputValue(event.target.value)}
              placeholder={defaultTimePerAnswer.toString()}
            />
            <p className="text-red-500 text-xs italic">{timePerAnswerError ? timePerAnswerError : <>&nbsp;</>}</p>
          </div>
        </>)}
        <p className="text-red-500 text-xs italic">{submissionErrorMessage ? submissionErrorMessage : <>&nbsp;</>}</p>
        <center>
          <BigColorBorderButton type="submit">
            Create Game
          </BigColorBorderButton>
        </center>
      </form>
    </div>
  );
}
