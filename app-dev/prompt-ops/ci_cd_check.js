/*
  Copyright 2025 Google LLC

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

      https://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
*/

import fs from "fs";
import { parse } from "csv-parse/sync";
import { GoogleGenerativeAI } from "@google/generative-ai";

// --- CONFIGURATION ---
const CONFIG = {
  MESSAGES_FILE_PATH: "messages.csv",
  MODEL_NAME: "gemini-2.5-flash",
  ACCURACY_THRESHOLD: 0.8, // 80%
  PROMPT_TEMPLATE:
    "Analyze the text and image (if there is one) of this social media " +
    "post. Determine if either the text or the image indicates that the " +
    "post is commercial spam. Text: {}",
};

// --- UTILITY FUNCTIONS ---

/**
 * Initializes the Google Generative AI client with the API key from
 * environment variables.
 * @returns {GoogleGenerativeAI} The initialized GenAI client.
 * @throws {Error} If the GEMINI_API_KEY is not found in the .env file.
 */
function initializeGenaiClient() {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    throw new Error(
      "GEMINI_API_KEY not found. Please set it in your .env file."
    );
  }
  return new GoogleGenerativeAI(apiKey);
}

/**
 * Loads and parses messages from a CSV file.
 * @param {string} filePath The path to the CSV file.
 * @returns {Array<Object>} An array of message objects, each with text,
 * is_spam, and image_path properties.
 */
function loadMessages(filePath) {
  const csvContent = fs.readFileSync(filePath, "utf8");
  return parse(csvContent, {
    columns: true,
    skip_empty_lines: true,
  }).map((record) => ({
    text: record.text,
    is_spam: record.spam.toLowerCase() === "true",
    image_path: record.image_path || "",
  }));
}

/**
 * Converts an image file to a GenerativePart object for the AI model.
 * @param {string} filePath The path to the image file.
 * @param {string} mimeType The MIME type of the image (e.g., "image/jpeg").
 * @returns {Object} A GenerativePart object containing the base64-encoded
 * image data.
 */
function fileToGenerativePart(filePath, mimeType) {
  const data = Buffer.from(fs.readFileSync(filePath)).toString("base64");
  return {
    inlineData: {
      data,
      mimeType,
    },
  };
}

// --- AI AND EVALUATION FUNCTIONS ---

/**
 * Sends a prompt (with an optional image) to the AI model and gets a spam
 * classification.
 * @param {GoogleGenerativeAI} genAI The initialized GenAI client.
 * @param {string} modelName The name of the model to use.
 * @param {string} prompt The text prompt to send to the model.
 * @param {string|null} imagePath The path to an optional image file.
 * @returns {Promise<Object>} A promise that resolves to the AI's JSON
 * response.
 */
async function getSpamResponseFromAI(
  genAI,
  modelName,
  prompt,
  imagePath = null
) {
  const model = genAI.getGenerativeModel({
    model: modelName,
    generationConfig: {
      temperature: 0.2,
      responseMimeType: "application/json",
      responseSchema: {
        type: "OBJECT",
        properties: {
          is_spam: { type: "BOOLEAN" },
          explanation: { type: "STRING" },
        },
        required: ["is_spam", "explanation"],
      },
    },
  });
  const parts = [{ text: prompt }];
  if (imagePath) {
    parts.push(fileToGenerativePart(imagePath, "image/jpeg"));
  }
  const result = await model.generateContent({ contents: [{ parts }] });
  return JSON.parse(result.response.text());
}

// --- EVALUATION WORKFLOW ---

/**
 * Evaluates a list of messages in parallel by sending them to the AI model.
 * @param {GoogleGenerativeAI} genAI The initialized GenAI client.
 * @param {Array<Object>} messages An array of message objects to evaluate.
 * @returns {Promise<Array<Object>>} A promise that resolves to an array of
 * settled promise results.
 */
async function evaluateMessages(genAI, messages) {
  console.log(`Evaluating ${messages.length} messages in parallel...`);
  const promises = messages.map((message) => {
    const fullPrompt = CONFIG.PROMPT_TEMPLATE.replace("{}", message.text);
    return getSpamResponseFromAI(
      genAI,
      CONFIG.MODEL_NAME,
      fullPrompt,
      message.image_path
    ).then((aiResponse) => ({ aiResponse, message }));
  });
  return Promise.allSettled(promises);
}

/**
 * Processes the results from the AI evaluation, counting correct
 * classifications.
 * @param {Array<Object>} results An array of settled promise results from
 * Promise.allSettled.
 * @returns {number} The total count of correctly classified messages.
 */
function processResults(results) {
  let correctCount = 0;
  for (const result of results) {
    if (result.status === "fulfilled") {
      const { aiResponse, message } = result.value;
      if (aiResponse.is_spam === message.is_spam) {
        correctCount++;
      } else {
        console.error(
          `Incorrect classification for message: "${message.text}"`
        );
        console.error(
          `  - Expected: ${message.is_spam}, Got: ${aiResponse.is_spam}`
        );
      }
    } else {
      console.error(`An error occurred during processing:`, result.reason);
    }
  }
  return correctCount;
}

/**
 * Calculates and reports the final accuracy, then exits the process.
 * @param {number} correctCount The number of correctly classified messages.
 * @param {number} totalMessages The total number of messages evaluated.
 */
function reportFinalResult(correctCount, totalMessages) {
  const accuracy = correctCount / totalMessages;
  console.log(`\nAccuracy: ${(accuracy * 100).toFixed(0)}%`);
  if (accuracy >= CONFIG.ACCURACY_THRESHOLD) {
    console.log(
      `✅ Accuracy is above the ${ 
        CONFIG.ACCURACY_THRESHOLD * 100
      }% threshold. CI/CD check passed.`
    );
    process.exit(0);
  } else {
    console.error(
      `❌ Accuracy is below the ${ 
        CONFIG.ACCURACY_THRESHOLD * 100
      }% threshold. CI/CD check failed.`
    );
    process.exit(1);
  }
}

// --- MAIN EXECUTION ---

/**
 * The main function that orchestrates the entire evaluation process.
 */
async function main() {
  console.log("Initializing...");
  const genAI = initializeGenaiClient();
  console.log("Loading messages...");
  const messages = loadMessages(CONFIG.MESSAGES_FILE_PATH);
  const results = await evaluateMessages(genAI, messages);
  const correctCount = processResults(results);
  reportFinalResult(correctCount, messages.length);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});