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
import { pipeline, cos_sim as cosSim } from "@xenova/transformers";

// --- CONFIGURATION ---
const CONFIG = {
  MESSAGES_FILE_PATH: "messages.csv",
  MODEL_NAME: "gemini-2.5-flash",
  PROMPT_TEMPLATES: [
    "Is this a commercial spam message? {}",
    "Analyze the text and image (if there is one) of this social media " +
      "post. Determine if it is commercial spam and provide a one-sentence " +
      "explanation for your reasoning. Text: {}",
  ],
  // Weights for the final recommendation score. Must add up to 1.0.
  SCORING_WEIGHTS: {
    accuracy: 0.7,
    similarity: 0.3,
  },
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
 * Initializes the Xenova/transformers feature-extraction pipeline.
 * This model is used to convert text into numerical vectors (embeddings).
 * @returns {Promise<Function>} A promise that resolves to the feature
 * extraction pipeline function.
 */
async function initializeExtractor() {
  return await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2");
}

/**
 * Loads and parses messages from a CSV file.
 * @param {string} filePath The path to the CSV file.
 * @returns {Array<Object>} An array of message objects.
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
    expected_explanation: record.expected_explanation || "",
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

/**
 * Calculates the cosine similarity between the embeddings of two strings.
 * @param {string} explanation1 The first string.
 * @param {string} explanation2 The second string.
 * @param {Function} extractor The feature extraction pipeline.
 * @returns {Promise<number>} A promise that resolves to the similarity score
 * (0 to 1).
 */
async function calculateSimilarity(explanation1, explanation2, extractor) {
  if (!explanation1 || !explanation2) return 0.0;
  const [e1, e2] = await Promise.all([
    extractor(explanation1, { pooling: "mean", normalize: true }),
    extractor(explanation2, { pooling: "mean", normalize: true }),
  ]);
  return cosSim(e1.data, e2.data);
}

/**
 * Evaluates a single message against a list of prompt templates.
 * @param {Object} message The message object to evaluate.
 * @param {Array<string>} promptTemplates An array of prompt templates.
 * @param {GoogleGenerativeAI} genAI The initialized GenAI client.
 * @param {string} modelName The name of the model to use.
 * @param {Function} extractor The feature extraction pipeline.
 * @returns {Promise<Object>} A promise that resolves to an object with
 * results for each template.
 */
async function evaluateMessage(
  message,
  promptTemplates,
  genAI,
  modelName,
  extractor
) {
  const results = {};
  for (const template of promptTemplates) {
    const fullPrompt = template.replace("{}", message.text);
    try {
      const aiResponse = await getSpamResponseFromAI(
        genAI,
        modelName,
        fullPrompt,
        message.image_path
      );
      const isCorrect = aiResponse.is_spam === message.is_spam;
      const similarity = await calculateSimilarity(
        aiResponse.explanation,
        message.expected_explanation,
        extractor
      );
      results[template] = { isCorrect, similarity };
    } catch (error) {
      console.error(
        `Error processing prompt "${template}" for message "${message.text}":`,
        error
      );
      results[template] = { isCorrect: false, similarity: 0.0 };
    }
  }
  return results;
}

// --- REPORTING FUNCTIONS ---

/**
 * Aggregates results from all message evaluations into a summary object.
 * @param {Array<Object>} evaluationResults An array of evaluation results
 * from evaluateMessage.
 * @returns {Object} An object summarizing the performance of each prompt
 * template.
 */
function aggregateResults(evaluationResults) {
  const aggregated = {};
  for (const result of evaluationResults) {
    for (const [template, data] of Object.entries(result)) {
      if (!aggregated[template]) {
        aggregated[template] = {
          correct: 0,
          total: 0,
          similarities: [],
        };
      }
      if (data.isCorrect) {
        aggregated[template].correct++;
      }
      aggregated[template].total++;
      aggregated[template].similarities.push(data.similarity);
    }
  }
  return aggregated;
}

/**
 * Prints the aggregated results to the console in a readable format.
 * @param {Object} aggregatedResults The aggregated results object from
 * aggregateResults.
 */
function printResults(aggregatedResults) {
  console.log("\n--- PROMPT EVALUATION RESULTS ---");
  for (const [template, data] of Object.entries(aggregatedResults)) {
    const accuracy =
      data.total > 0 ? ((data.correct / data.total) * 100).toFixed(0) : 0;
    const avgSimilarity =
      data.similarities.length > 0
        ? (data.similarities.reduce((a, b) => a + b, 0) /
            data.similarities.length) *
          100
        : 0;
    console.log(`\nPrompt: "${template}"`);
    console.log(`  - Accuracy: ${accuracy}% (${data.correct}/${data.total})`);
    console.log(
      `  - Explanation Similarity: ${avgSimilarity.toFixed(0)}% (avg. cosine)`
    );
  }
}

/**
 * Recommends the best prompt based on a weighted score of accuracy and
 * similarity.
 * @param {Object} aggregatedResults The aggregated results object from
 * aggregateResults.
 */
function recommendBestPrompt(aggregatedResults) {
  let bestPrompt = null;
  let bestScore = -1;
  for (const [template, data] of Object.entries(aggregatedResults)) {
    const accuracy = data.total > 0 ? data.correct / data.total : 0;
    const avgSimilarity =
      data.similarities.length > 0
        ? data.similarities.reduce((a, b) => a + b, 0) /
          data.similarities.length
        : 0;
    const score =
      accuracy * CONFIG.SCORING_WEIGHTS.accuracy +
      avgSimilarity * CONFIG.SCORING_WEIGHTS.similarity;
    if (score > bestScore) {
      bestScore = score;
      bestPrompt = template;
    }
  }
  console.log("\n--- RECOMMENDATION ---");
  if (bestPrompt) {
    console.log(
      "Based on a combined score of accuracy and explanation similarity, " +
        "the recommended prompt is:\n" +
        bestPrompt
    );
  } else {
    console.log("No data to recommend a prompt.");
  }
}

// --- MAIN EXECUTION ---

/**
 * Runs the core evaluation logic, processing all messages in parallel.
 * @param {Array<Object>} messages The messages to evaluate.
 * @param {GoogleGenerativeAI} genAI The initialized GenAI client.
 * @param {Function} extractor The initialized feature extractor.
 * @returns {Promise<Array<Object>>} A promise that resolves to the full
 * list of evaluation results.
 */
async function runEvaluation(messages, genAI, extractor) {
  console.log(
    `Evaluating ${messages.length} messages against ` +
      `${CONFIG.PROMPT_TEMPLATES.length} prompts in parallel...`
  );
  const promises = messages.map((message) =>
    evaluateMessage(
      message,
      CONFIG.PROMPT_TEMPLATES,
      genAI,
      CONFIG.MODEL_NAME,
      extractor
    )
  );
  return Promise.all(promises);
}

/**
 * The main function that orchestrates the entire prompt comparison process.
 */
async function main() {
  console.log("Initializing...");
  const genAI = initializeGenaiClient();
  const extractor = await initializeExtractor();
  console.log("Loading messages...");
  const messages = loadMessages(CONFIG.MESSAGES_FILE_PATH);
  const evaluationResults = await runEvaluation(messages, genAI, extractor);
  const aggregatedResults = aggregateResults(evaluationResults);
  printResults(aggregatedResults);
  recommendBestPrompt(aggregatedResults);
}

main().catch(console.error);
