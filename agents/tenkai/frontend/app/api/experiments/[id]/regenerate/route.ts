import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { getExperiment } from '@/lib/api';

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id: idStr } = await params;
        const id = parseInt(idStr);
        if (isNaN(id)) {
            return NextResponse.json({ error: 'Invalid ID' }, { status: 400 });
        }

        const exp = await getExperiment(id);
        if (!exp) {
            return NextResponse.json({ error: 'Experiment not found' }, { status: 404 });
        }

        // Determine experiment directory from the result path stored in DB
        // resultsPath is typically .../experiments/runs/<folder>/results.json
        const resultsPath = exp.results_path;
        const experimentDir = path.dirname(resultsPath);

        const rootDir = path.resolve(process.cwd(), '..');
        // Trigger Tenkai binary from PATH in report-only mode
        const cmd = 'tenkai';
        const args = ['-experiment-id', String(id)];

        // We run synchronously-ish or detach? 
        // Report generation is fast, so we can probably wait for it to ensure it's done before returning.

        return new Promise<NextResponse>((resolve, reject) => {
            const child = spawn('tenkai', args, {
                cwd: rootDir,
                env: { ...process.env, PATH: process.env.PATH },
                // Wait for completion for regeneration since we need the result immediately?
                // Actually original code waited? No, it used exec before?
                // Original spawn was fire-and-forget but regenerate usually blocks? 
                // "WaitMsBeforeAsync" suggests it might be async.
                // But here we're in an API route. 
                // Let's keep it detached but maybe capture logs if needed.
                // Original was just spawn('tenkai', ...).
            }); let stdoutData = '';

            child.stdout.on('data', (data) => {
                stdoutData += data.toString();
                console.log(`[Tenkai CLI] ${data}`);
            });

            let stderrData = '';
            child.stderr.on('data', (data) => {
                stderrData += data.toString();
                console.error(`[Tenkai CLI Error] ${data}`);
            });

            child.on('close', (code) => {
                if (code === 0) {
                    resolve(NextResponse.json({ message: 'Report regenerated successfully' }));
                } else {
                    console.error(`Regeneration failed (code ${code}). Stderr: ${stderrData}`);
                    resolve(NextResponse.json({ error: `Process exited with code ${code}: ${stderrData}` }, { status: 500 }));
                }
            });

            child.on('error', (err) => {
                console.error('Spawn error:', err);
                resolve(NextResponse.json({ error: 'Failed to spawn process' }, { status: 500 }));
            });
        });

    } catch (error) {
        console.error('Failed to regenerate report:', error);
        return NextResponse.json({ error: 'Failed to regenerate report' }, { status: 500 });
    }
}
