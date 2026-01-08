const Database = require('better-sqlite3');
const db = new Database(':memory:');

try {
    db.prepare(`
    CREATE TABLE IF NOT EXISTS experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        timestamp DATETIME
    );`).run();

    db.prepare(`
    CREATE TABLE IF NOT EXISTS run_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        experiment_id INTEGER,
        is_success BOOLEAN DEFAULT 0
    );`).run();

    db.prepare(`
        SELECT 
            e.*,
            (SELECT COUNT(*) FROM run_results WHERE experiment_id = e.id AND is_success = 1) as success_count,
            (SELECT COUNT(*) FROM run_results WHERE experiment_id = e.id) as total_runs
        FROM experiments e 
        ORDER BY timestamp DESC
    `).all();
    console.log("Query success");
} catch (e) {
    console.error(e);
}
