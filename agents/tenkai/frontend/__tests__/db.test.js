const Database = require('better-sqlite3');

describe('Database Queries', () => {
    let db;

    beforeEach(() => {
        db = new Database(':memory:');
        
        // Setup schema
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
    });

    afterEach(() => {
        db.close();
    });

    test('getExperiments query syntax is valid', () => {
        expect(() => {
            // Updated query using JOINs
            db.prepare(`
                SELECT 
                    e.*,
                    COUNT(CASE WHEN r.is_success = 1 THEN 1 END) as success_count,
                    COUNT(r.id) as total_runs
                FROM experiments e
                LEFT JOIN run_results r ON e.id = r.experiment_id
                GROUP BY e.id
                ORDER BY e.timestamp DESC
            `).all();
        }).not.toThrow();
    });

    test('getExperiments returns correct counts', () => {
        // Insert test data
        const exp = db.prepare('INSERT INTO experiments (name, timestamp) VALUES (?, ?)').run('test-exp', '2024-01-01');
        const expId = exp.lastInsertRowid;

        // 1 success, 1 fail
        db.prepare('INSERT INTO run_results (experiment_id, is_success) VALUES (?, 1)').run(expId);
        db.prepare('INSERT INTO run_results (experiment_id, is_success) VALUES (?, 0)').run(expId);

        const row = db.prepare(`
            SELECT 
                e.*,
                COUNT(CASE WHEN r.is_success = 1 THEN 1 END) as success_count,
                COUNT(r.id) as total_runs
            FROM experiments e
            LEFT JOIN run_results r ON e.id = r.experiment_id
            GROUP BY e.id
            ORDER BY e.timestamp DESC
        `).get();

        expect(row.success_count).toBe(1);
        expect(row.total_runs).toBe(2);
    });
});
