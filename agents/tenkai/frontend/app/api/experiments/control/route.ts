import { NextRequest, NextResponse } from 'next/server';
import Database from 'better-sqlite3';
import path from 'path';

export async function POST(req: NextRequest) {
    let db;
    try {
        const { id, action } = await req.json();

        if (!id || !action) {
            return NextResponse.json({ error: 'Missing id or action' }, { status: 400 });
        }

        const dbPath = path.join(process.cwd(), '..', 'experiments', 'tenkai.db');
        db = new Database(dbPath);
        db.pragma('busy_timeout = 5000');

        const stmt = db.prepare('UPDATE experiments SET execution_control = ? WHERE id = ?');
        stmt.run(action, id);

        return NextResponse.json({ message: `Action ${action} recorded in DB`, action });
    } catch (error) {
        console.error('Failed to record control action in DB:', error);
        return NextResponse.json({ error: 'Failed to record control action' }, { status: 500 });
    } finally {
        if (db) db.close();
    }
}
