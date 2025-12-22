import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

export async function DELETE(req: NextRequest) {
    try {
        const dbPath = process.env.DB_PATH || path.join(process.cwd(), '..', 'experiments', 'tenkai.db');
        const db = new Database(dbPath);

        const deleteTx = db.transaction(() => {
            db.prepare('DELETE FROM tool_usage').run();
            db.prepare('DELETE FROM messages').run();
            db.prepare('DELETE FROM test_results').run();
            db.prepare('DELETE FROM lint_results').run();
            db.prepare('DELETE FROM run_files').run();
            db.prepare('DELETE FROM run_results').run();
            db.prepare('DELETE FROM experiments').run();
        });

        deleteTx();
        db.close();

        return NextResponse.json({ message: 'All experiments deleted' });
    } catch (error) {
        console.error('Failed to delete all experiments:', error);
        return NextResponse.json({ error: 'Failed to delete all experiments' }, { status: 500 });
    }
}
