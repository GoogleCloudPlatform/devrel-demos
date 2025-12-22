import { NextRequest, NextResponse } from 'next/server';
import { revalidatePath } from 'next/cache';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(req: NextRequest) {
    try {
        const { name, template, reps, concurrent, alternatives, scenarios, control } = await req.json();

        const rootDir = path.join(process.cwd(), '..');
        const configPath = path.join(rootDir, 'experiments', 'templates', template, 'config.yaml');

        // Trigger Tenkai binary from PATH
        const cmd = 'tenkai';
        const args = [
            '-config', configPath,
            '-reps', reps.toString(),
            '-concurrent', concurrent.toString()
        ];

        if (name) {
            args.push('-name', name);
        }

        if (control) {
            args.push('-control', control);
        }

        if (alternatives && Array.isArray(alternatives) && alternatives.length > 0) {
            args.push('-alternatives', alternatives.join(','));
        }

        if (scenarios && Array.isArray(scenarios) && scenarios.length > 0) {
            args.push('-scenarios', scenarios.join(','));
        }

        console.log(`Executing: ${cmd} ${args.join(' ')}`);

        console.log(`[Run] Spawning tenkai binary from PATH`);

        const child = spawn('tenkai', args, {
            cwd: rootDir,
            env: { ...process.env, PATH: process.env.PATH },
            stdio: 'ignore' // detach completely
        });

        child.unref();

        // Revalidate the dashboard to show the new 'running' experiment
        revalidatePath('/');

        return NextResponse.json({ message: 'Experiment started', template });
    } catch (error) {
        console.error('Failed to trigger experiment:', error);
        return NextResponse.json({ error: 'Failed to trigger experiment' }, { status: 500 });
    }
}
