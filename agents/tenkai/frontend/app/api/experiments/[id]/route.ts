import { NextRequest, NextResponse } from 'next/server';
import { getExperiment } from '@/lib/api';
import Database from 'better-sqlite3';
import path from 'path';

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id: idStr } = await params;
        const id = parseInt(idStr);
        if (isNaN(id)) {
            return NextResponse.json({ error: 'Invalid ID' }, { status: 400 });
        }

        const dbPath = process.env.DB_PATH || path.join(process.cwd(), '..', 'experiments', 'tenkai.db');
        const db = new Database(dbPath);

        // Transaction to ensure consistency
        const deleteTx = db.transaction(() => {
            const runIds = db.prepare('SELECT id FROM run_results WHERE experiment_id = ?').all(id).map((r: any) => r.id);

            if (runIds.length > 0) {
                db.prepare('DELETE FROM tool_usage WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)').run(id);
                db.prepare('DELETE FROM messages WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)').run(id);
                db.prepare('DELETE FROM test_results WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)').run(id);
                db.prepare('DELETE FROM lint_results WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)').run(id);
                db.prepare('DELETE FROM run_files WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)').run(id);
            }

            db.prepare('DELETE FROM run_results WHERE experiment_id = ?').run(id);
            db.prepare('DELETE FROM experiments WHERE id = ?').run(id);
        });

        deleteTx();
        db.close();

        return NextResponse.json({ message: 'Experiment deleted' });
    } catch (error) {
        console.error('Failed to delete experiment:', error);
        return NextResponse.json({ error: 'Failed to delete experiment' }, { status: 500 });
    }
}
