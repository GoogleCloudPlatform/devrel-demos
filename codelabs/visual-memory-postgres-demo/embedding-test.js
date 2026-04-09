const { GoogleGenAI } = require('@google/genai');
require('dotenv').config();

async function main() {
  const ai = new GoogleGenAI({ vertexai: true, });

  console.log("Connected to Gemini API");

  const response = await ai.models.embedContent({
    model: 'gemini-embedding-001',
    contents: 'What is the meaning of life?',
    config: { outputDimensionality: 768 },
  });

  const embeddingLength = response.embeddings[0].values.length;
  console.log(`Length of embedding: ${embeddingLength}`);
}

main();