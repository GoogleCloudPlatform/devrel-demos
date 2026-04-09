const express = require('express');
const { Pool } = require('pg');
const { GoogleGenAI } = require('@google/genai');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static('public'));

// Configure Postgres Connection
const pool = new Pool({
  host: process.env.DB_HOST || '127.0.0.1',
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER,
  password: process.env.DB_PASS,
  database: process.env.DB_NAME,
});

const ai = new GoogleGenAI({
  vertexai: true,
  project: process.env.PROJECT_ID || process.env.GOOGLE_CLOUD_PROJECT,
  location: process.env.REGION || 'us-central1'
});

// Helper: Ensure we have a user and conversation ID
async function ensureUserSession(req) {
  let { userId, conversationId } = req.body;
  if (!userId) {
    const userResult = await pool.query(`INSERT INTO users (persona_name) VALUES ('Session User') RETURNING id`);
    userId = userResult.rows[0].id;
  }
  if (!conversationId) {
    const convResult = await pool.query(`INSERT INTO conversations (user_id) VALUES ($1) RETURNING id`, [userId]);
    conversationId = convResult.rows[0].id;
  }
  return { userId, conversationId };
}

// 1. CHAT ENDPOINT
app.post('/api/chat', async (req, res) => {
  try {
    const { message } = req.body;
    const { userId, conversationId } = await ensureUserSession(req);

    // Fetch last AI message for context in extraction
    const lastAiMsgResult = await pool.query(
      `SELECT content FROM messages 
       WHERE conversation_id = $1 AND role = 'ai' 
       ORDER BY id DESC LIMIT 1`,
      [conversationId]
    );
    const lastAiMessage = lastAiMsgResult.rows[0]?.content || null;

    // Save User Message
    const userMsgResult = await pool.query(
      `INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3) RETURNING id`,
      [conversationId, 'user', message]
    );
    const userMessageId = userMsgResult.rows[0].id;

    // Retrieve Similar Memories for Context (Using pgvector)
    const promptEmbeddingRes = await ai.models.embedContent({
      model: 'gemini-embedding-001',
      contents: message,
      config: { outputDimensionality: 768 },
    });

    const promptEmbedding = promptEmbeddingRes.embeddings[0].values;
    // Format embedding as pgvector string: '[x, y, z...]'
    const embeddingStr = `[${promptEmbedding.join(',')}]`;

    // Query DB for memories within a threshold (similarity > 0.4) with a max limit of 20
    const relevantMemories = await pool.query(
      `SELECT id, content, memory_type, category 
       FROM memories 
       WHERE user_id = $1 AND 1 - (embedding <=> $2::vector) > 0.4
       ORDER BY embedding <=> $2::vector 
       LIMIT 12`,
      [userId, embeddingStr]
    );

    // Log the telemetry
    await pool.query(
      `INSERT INTO queries_log (user_id, natural_query, search_embedding) VALUES ($1, $2, $3)`,
      [userId, message, embeddingStr]
    );

    // Get user's persona name for the prompt
    const userResult = await pool.query(`SELECT persona_name FROM users WHERE id = $1`, [userId]);
    const personaName = userResult.rows[0]?.persona_name || 'User';

    // Fetch all messages for context (excluding the one we just saved!)
    const historyResult = await pool.query(
      `SELECT role, content FROM messages 
       WHERE conversation_id = $1 AND id < $2
       ORDER BY id DESC`,
      [conversationId, userMessageId]
    );

    // Reverse to get chronological order
    const history = historyResult.rows.reverse();

    // Construct history array for Chats SDK
    const historyArray = [];

    // Add history turns
    history.forEach(msg => {
      historyArray.push({
        role: msg.role === 'user' ? 'user' : 'model',
        parts: [{ text: msg.content }]
      });
    });

    // Format memory context and instructions
    let memoryContext = `You are ${personaName}'s personal assistant. Use the following facts to respond gracefully. When using a memory to make a recommendation or answer, explicitly reference it (e.g., "Since you like gardening..." or "I know you are an engineer..."). Do not say "based on my memory bank", just state what you know about the user naturally.\n\nMemories:\n`;
    relevantMemories.rows.forEach(m => {
      memoryContext += `- ${m.content} (Type: ${m.memory_type}, Category: ${m.category})\n`;
    });

    const systemInstruction = memoryContext + `
You are a proactive personal assistant with a "how can I help" mentality. Your goal is to actively solve problems and offer solutions without being asked for every step.

Key Behaviors:
1. **Offer Alternatives Immediately**: If the user indicates they have already seen, read, or done something you suggested (e.g., "I've read that one"), IMMEDIATELY offer 2-3 alternatives. Do not wait for them to ask for more.
2. **Act on Feedback**: If the user gives feedback on your output (e.g., "that's too formal", "make it shorter", "try again"), IMMEDIATELY generate a new version that incorporates the feedback. Do not just acknowledge the feedback or ask what to do.
3. **Be Proactive**: Don't just answer questions passively. Ask follow-up questions, suggest next steps, and use the user's memories to personalize the experience and anticipate their needs.
4. **Explicitly Reference Memories**: When drawing on the user's memories to make suggestions or provide answers, explicitly state the memory you are referencing (e.g., "Since you are an engineer...", "I know you prefer dark mode..."). This shows you remember them.

Examples of correct behavior:
User: "I've read that one already."
Assistant: "Got it! Since you've already read that, here are 3 more books you might enjoy: [Book A], [Book B], [Book C]."

User: "That's too formal for me."
Assistant: "Understood! Here is a less formal version: [New Draft content]."`;

    // Prepend system instruction to the first message in history or current message
    if (historyArray.length > 0) {
      historyArray[0].parts[0].text = systemInstruction + "\n\n" + historyArray[0].parts[0].text;
    }

    // Create chat session
    const chat = ai.chats.create({
      model: 'gemini-2.5-flash',
      history: historyArray
    });

    // Send the current message (prepend if no history)
    let finalMessage = message;
    if (historyArray.length === 0) {
      finalMessage = systemInstruction + "\n\n" + message;
    }

    const chatResult = await chat.sendMessage({
      message: finalMessage
    });
    const aiResponse = chatResult.text;

    // Save AI message
    await pool.query(
      `INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3)`,
      [conversationId, 'ai', aiResponse]
    );

    // Trigger Memory Extraction Pipeline in the background
    extractMemoriesAsync(message, userId, userMessageId, lastAiMessage)
      .catch(err => console.error("Error in background extraction:", err));

    res.json({
      userId,
      conversationId,
      response: aiResponse,
      memoriesUsed: relevantMemories.rows
    });
  } catch (err) {
    console.error("Error in /api/chat:", err);
    res.status(500).json({ error: "Failed to process chat" });
  }
});

// MEMORY EXTRACTION LOGIC
async function extractMemoriesAsync(userMessage, userId, messageId, context = null) {
  let prompt = `Analyze the following user message. We are building a memory profile for this user.`;
  if (context) {
    prompt += `\nContext (Previous AI Message): "${context}"`;
  }
  prompt += `\nUser Message: "${userMessage}"
    
    Extract ANY explicit facts (Facts), preferences (Pref), or implicit behavioral traits/styles (Implicit) about the user themselves.
    CRITICAL: Do NOT extract memories about the user asking you questions, asking for a summary of themselves, asking what you remember, or testing your memory. Only extract facts about the user's life, preferences, and traits. For example, ignore "User asked for a summary" or "User is asking if I remember their dog".
    Return the result as a raw JSON array of objects (NO Markdown blocks, just the JSON array).
    Format: [{"content": "string fact/sentence", "type": "FACT|PREF|IMPLICIT", "category": "General|Travel|Hobby|Persona"}]
    If nothing is found, return [].`;

  const extractionPrompt = prompt;

  const result = await ai.models.generateContent({
    model: 'gemini-2.5-flash',
    contents: extractionPrompt
  });
  let rawJson = result.text.replace(/^```json/g, '').replace(/```$/g, '').trim();

  let extracted;
  try {
    extracted = JSON.parse(rawJson);
  } catch (e) {
    console.warn("Could not parse extracted JSON:", rawJson);
    return [];
  }

  const addedIds = [];
  if (Array.isArray(extracted) && extracted.length > 0) {
    // Compute embeddings and save each to the DB
    for (const memory of extracted) {
      const embedRes = await ai.models.embedContent({
        model: 'gemini-embedding-001',
        contents: memory.content,
        config: { outputDimensionality: 768 },
      });
      const vectorData = `[${embedRes.embeddings[0].values.join(',')}]`;

      // Check for duplicates (semantic similarity > 0.85)
      const duplicateCheck = await pool.query(
        `SELECT content FROM memories 
         WHERE user_id = $1 AND 1 - (embedding <=> $2::vector) > 0.85
         LIMIT 1`,
        [userId, vectorData]
      );

      if (duplicateCheck.rows.length > 0) {
        console.log(`Skipping duplicate memory: "${memory.content}" (Matches existing: "${duplicateCheck.rows[0].content}")`);
        continue;
      }

      const insertResult = await pool.query(
        `INSERT INTO memories (user_id, content, memory_type, category, embedding, source_message_id)
                 VALUES ($1, $2, $3, $4, $5, $6) RETURNING id`,
        [userId, memory.content, memory.type.toUpperCase(), memory.category, vectorData, messageId]
      );
      addedIds.push(insertResult.rows[0].id);
      console.log(`Saved new memory: ${memory.content}`);
    }
  }
  return addedIds;
}

// 2. FETCH ALL MEMORIES ENDPOINT (For the 2D Visualization)
app.get('/api/memories', async (req, res) => {
  try {
    const { userId } = req.query;
    if (!userId) return res.json({ nodes: [], links: [] });

    // Fetch all memories for the user
    const result = await pool.query(
      `SELECT id, content, memory_type, category, embedding::text as vector 
             FROM memories WHERE user_id = $1 ORDER BY id`, [userId]
    );

    const allFacts = result.rows;
    const uniqueEdges = {};
    const nodeConnectionCount = {};
    allFacts.forEach(row => {
      nodeConnectionCount[row.id] = 0;
    });

    // Query for similar facts using PGVector
    for (const row of allFacts) {
      const neighborsQuery = await pool.query(`
        SELECT id, 1 - (embedding <=> $1) as similarity
        FROM memories
        WHERE id != $2 AND user_id = $3
        ORDER BY embedding <=> $1 ASC
        LIMIT 6
      `, [row.vector, row.id, userId]);

      for (const neighbor of neighborsQuery.rows) {
        // Sort IDs so a->b and b->a are the same edge key
        const edgeKeyPair = [row.id, neighbor.id].sort((a, b) => a - b).join('-');

        if (!uniqueEdges[edgeKeyPair]) {
          const thickness = Math.pow(neighbor.similarity, 3) * 50;
          uniqueEdges[edgeKeyPair] = {
            source: row.id,
            target: neighbor.id,
            value: thickness,
            similarity: neighbor.similarity
          };
          nodeConnectionCount[row.id] += 1;
          nodeConnectionCount[neighbor.id] += 1;
        }
      }
    }

    const links = Object.values(uniqueEdges);

    const nodes = allFacts.map(row => {
      const count = nodeConnectionCount[row.id] || 0;
      return {
        id: row.id,
        name: row.content,
        type: row.memory_type,
        category: row.category,
        size: 6 + (count * 2) // dynamic sizing based on connections
      };
    });

    res.json({ nodes, links });
  } catch (err) {
    console.error("Error fetching memories:", err);
    res.status(500).json({ error: "Failed to fetch memories" });
  }
});

// Simple Cosine Similarity Function
function cosineSimilarity(A, B) {
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < A.length; i++) {
    dotProduct += A[i] * B[i];
    normA += A[i] * A[i];
    normB += B[i] * B[i];
  }
  if (normA === 0 || normB === 0) return 0;
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

// Persona Pool for quick access
let personaPool = [];

const PERSONAS_FILE = path.join(__dirname, 'personas.json');

async function generatePersonaPool() {
  if (fs.existsSync(PERSONAS_FILE)) {
    console.log("Loading persona pool from file...");
    try {
      personaPool = JSON.parse(fs.readFileSync(PERSONAS_FILE, 'utf8'));
      console.log(`Loaded ${personaPool.length} personas from file.`);
      return personaPool;
    } catch (e) {
      console.error("Error reading personas.json, will generate new ones:", e);
    }
  }

  console.log("Generating persona pool of 10 items...");
  try {
    const prompt = `Generate a list of 10 distinct synthetic personas for a user of an AI assistant. 
    For each, provide a Name (e.g. 'Elena - The Busy Exec' or 'David - The Tech Bro') and a detailed paragraph written in the first person (e.g. starting with "Hi, I'm [Name]...") introducing themselves with at least 15-20 distinct facts (hobbies, preferences, background, habits).
    Return the result as JSON matching the schema.`;

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
        responseSchema: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              description: { type: 'string' }
            },
            required: ['name', 'description']
          }
        }
      }
    });

    personaPool = JSON.parse(response.text.trim());
    console.log(`Generated ${personaPool.length} personas for the pool.`);

    // Save to file so we don't have to generate again
    try {
      fs.writeFileSync(PERSONAS_FILE, JSON.stringify(personaPool, null, 2));
      console.log("Saved personas to personas.json");
    } catch (e) {
      console.error("Error saving personas to file:", e);
    }

    return personaPool;
  } catch (err) {
    console.error("Error generating persona pool:", err);
  }
}

// GENERATE A SYNTHETIC PERSONA
app.get('/api/generate-persona', async (req, res) => {
  try {
    // 1. Load personas from file
    let personas = [];
    if (fs.existsSync(PERSONAS_FILE)) {
      personas = JSON.parse(fs.readFileSync(PERSONAS_FILE, 'utf8'));
    } else {
      personas = await generatePersonaPool();
    }

    // 2. Get existing users from DB
    const existingUsersResult = await pool.query(`SELECT persona_name FROM users`);
    const existingNames = existingUsersResult.rows.map(r => r.persona_name);

    // 3. Find an unused persona
    const unusedPersona = personas.find(p => !existingNames.includes(p.name));

    if (unusedPersona) {
      console.log(`Serving persona from file: ${unusedPersona.name}`);
      return res.json(unusedPersona);
    }

    // 4. If all used
    console.log("All personas from file are already in use.");
    return res.status(400).json({
      error: "All 10 personas have been used. Please reset the database to start over.",
      allUsed: true 
    });

  } catch (err) {
    console.error("Error generating persona:", err);
    res.status(500).json({ error: "Failed to generate persona" });
  }
});

// CREATE A NEW USER
app.post('/api/users', async (req, res) => {
  try {
    console.log("POST /api/users req.body:", req.body);
    const { persona_name } = req.body || {};
    if (!persona_name) return res.status(400).json({ error: "Missing persona_name" });

    const result = await pool.query(
      `INSERT INTO users (persona_name) VALUES ($1) RETURNING *`,
      [persona_name]
    );
    res.json(result.rows[0]);
  } catch (err) {
    console.error("Error creating user:", err);
    res.status(500).json({ error: "Failed to create user" });
  }
});

// FETCH ALL USERS
app.get('/api/users', async (req, res) => {
  try {
    const result = await pool.query(`SELECT * FROM users ORDER BY created_at DESC`);
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching users:", err);
    res.status(500).json({ error: "Failed to fetch users" });
  }
});

// FETCH CONVERSATIONS FOR USER
app.get('/api/conversations/:userId', async (req, res) => {
  try {
    const { userId } = req.params;
    const result = await pool.query(
      `SELECT * FROM conversations WHERE user_id = $1 ORDER BY started_at DESC`,
      [userId]
    );
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching conversations:", err);
    res.status(500).json({ error: "Failed to fetch conversations" });
  }
});

// FETCH MESSAGES FOR CONVERSATION
app.get('/api/messages/:conversationId', async (req, res) => {
  try {
    const { conversationId } = req.params;
    const result = await pool.query(
      `SELECT * FROM messages WHERE conversation_id = $1 ORDER BY created_at ASC`,
      [conversationId]
    );
    res.json(result.rows);
  } catch (err) {
    console.error("Error fetching messages:", err);
    res.status(500).json({ error: "Failed to fetch messages" });
  }
});

// SEED DEMO USER & MEMORIES
app.post('/api/seed', async (req, res) => {
  try {
    // 1. Create Demo User
    const userResult = await pool.query(
      `INSERT INTO users (persona_name) VALUES ('Demo User') RETURNING id`
    );
    const userId = userResult.rows[0].id;

    // 2. Create Initial Conversation
    const convResult = await pool.query(
      `INSERT INTO conversations (user_id) VALUES ($1) RETURNING id`,
      [userId]
    );
    const conversationId = convResult.rows[0].id;

    // 3. Example Memories to Seed
    const seedMemories = [
      { content: "User works as a software engineer at a startup.", type: "FACT", category: "Career" },
      { content: "User prefers dark mode for all their applications.", type: "PREF", category: "General" },
      { content: "User speaks enthusiastically about artificial intelligence.", type: "IMPLICIT", category: "Persona" },
      { content: "User drinks 3 cups of coffee every morning.", type: "FACT", category: "Habit" },
      { content: "User enjoys hiking in the Pacific Northwest.", type: "FACT", category: "Hobby" },
      { content: "User dislikes crowded tourist traps.", type: "PREF", category: "Travel" },
      { content: "User writes concise, action-oriented messages.", type: "IMPLICIT", category: "Communication" },
      { content: "User owns a 3-year-old golden retriever named Max.", type: "FACT", category: "Pets" },
      { content: "User wants to learn Rust programming in the next 6 months.", type: "PREF", category: "Learning" },
      { content: "User uses highly technical vocabulary casually.", type: "IMPLICIT", category: "Communication" },
      { content: "User is allergic to peanuts.", type: "FACT", category: "Health" },
      { content: "User prefers MacOS over Windows.", type: "PREF", category: "Technology" },
      { content: "User tends to ask follow-up questions.", type: "IMPLICIT", category: "Persona" },
      { content: "User visited Japan twice in 2023.", type: "FACT", category: "Travel" },
      { content: "User loves authentic ramen but hates sushi.", type: "PREF", category: "Food" },
      { content: "User values efficiency and quick responses.", type: "IMPLICIT", category: "Persona" },
      { content: "User plays electric guitar.", type: "FACT", category: "Hobby" },
      { content: "User mostly listens to classic rock and synthwave.", type: "PREF", category: "Music" },
      { content: "User exhibits a dry sense of humor.", type: "IMPLICIT", category: "Persona" },
      { content: "User bought a new home in Seattle last year.", type: "FACT", category: "Life" },
      { content: "User avoids taking morning meetings when possible.", type: "PREF", category: "Career" },
      { content: "User frequently expresses gratitude.", type: "IMPLICIT", category: "Behavior" },
      { content: "User ran a half-marathon in under 2 hours.", type: "FACT", category: "Health" },
      { content: "User prefers sci-fi over fantasy books.", type: "PREF", category: "Entertainment" },
      { content: "User tends to be skeptical of marketing claims.", type: "IMPLICIT", category: "Persona" },
    ];

    // Create a dummy message to tie the memories to
    const msgResult = await pool.query(
      `INSERT INTO messages (conversation_id, role, content) VALUES ($1, $2, $3) RETURNING id`,
      [conversationId, 'user', "Hello, I am the demo user."]
    );
    const messageId = msgResult.rows[0].id;

    // 4. Compute embeddings and insert them into DB
    const insertPromises = seedMemories.map(async (memory) => {
      const embedRes = await ai.models.embedContent({
        model: 'gemini-embedding-001',
        contents: memory.content,
        config: { outputDimensionality: 768 },
      });
      const vectorData = `[${embedRes.embeddings[0].values.join(',')}]`;

      return pool.query(
        `INSERT INTO memories (user_id, content, memory_type, category, embedding, source_message_id)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [userId, memory.content, memory.type.toUpperCase(), memory.category, vectorData, messageId]
      );
    });

    await Promise.all(insertPromises);

    res.json({ message: "Seed successful", userId, conversationId, memoryCount: seedMemories.length });
  } catch (err) {
    console.error("Error during seed:", err);
    res.status(500).json({ error: "Seed failed" });
  }
});

// RESET DATABASE (Clear and Reseed)
app.post('/api/reset', async (req, res) => {
  console.log("POST /api/reset received");
  console.log("Reset requested. Running seed.js...");
  exec('node seed.js', (error, stdout, stderr) => {
    if (error) {
      console.error(`exec error: ${error}`);
      return res.status(500).json({ error: "Reset failed", details: stderr });
    }
    console.log(`stdout: ${stdout}`);
    console.error(`stderr: ${stderr}`);
    res.json({ message: "Reset successful", log: stdout });
  });
});

if (require.main === module) {
  app.listen(port, () => {
    console.log(`Living Memory Demo Backend listening at http://localhost:${port}`);
  });
}

module.exports = {
  extractMemoriesAsync,
  generatePersonaPool,
  pool,
  ai
};
