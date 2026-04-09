require('dotenv').config();
const { pool, extractMemoriesAsync, generatePersonaPool } = require('./server.js');



async function seedDatabase() {
  try {
    console.log("Starting DB Wipe...");
    
    // Wipe everything (ON DELETE CASCADE will handle memories, messages, collabs via user_id)
    await pool.query('DELETE FROM users');
    
    console.log("Database wiped perfectly. Starting seed process...");

    const personas = await generatePersonaPool();
    const selectedPersonas = personas.slice(0, 2);

    for (const persona of selectedPersonas) {
      console.log(`\nCreating User: ${persona.name}...`);
      
      // Create User directly in DB
      const userResult = await pool.query(
        `INSERT INTO users (persona_name) VALUES ($1) RETURNING id`,
        [persona.name]
      );
      const userId = userResult.rows[0].id;
      
      // Create Conversation directly in DB
      const convResult = await pool.query(
        `INSERT INTO conversations (user_id) VALUES ($1) RETURNING id`,
        [userId]
      );
      const conversationId = convResult.rows[0].id;
      
      console.log(`Sending intro message for ${persona.name}...`);
      
      // Insert Message directly in DB
      const msgResult = await pool.query(
        `INSERT INTO messages (conversation_id, role, content) VALUES ($1, 'user', $2) RETURNING id`,
        [conversationId, persona.description]
      );
      const messageId = msgResult.rows[0].id;
      
      // Extract memories directly!
      await extractMemoriesAsync(persona.description, userId, messageId);
      
      console.log(`Intro message sent and memories extracted.`);
    }

    console.log("\n✅ Entire database successfully seeded with Demo Data!");
    process.exit(0);

  } catch (err) {
    console.error("FATAL ERROR during seed:", err);
    process.exit(1);
  }
}

seedDatabase();
