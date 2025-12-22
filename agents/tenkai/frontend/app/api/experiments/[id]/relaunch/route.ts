import { NextRequest, NextResponse } from 'next/server';
import { getExperiment, getRunResults } from '@/lib/api';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;
        const experimentId = parseInt(id);
        const experiment = getExperiment(experimentId);

        if (!experiment) {
            return NextResponse.json({ error: 'Experiment not found' }, { status: 404 });
        }

        // Detect correct root dir (parent of frontend)
        const rootDir = path.resolve(process.cwd(), '..');

        // Command Construction
        const cmd = 'tenkai';
        const args = [
            '-config', experiment.config_path,
            '-reps', experiment.reps.toString(),
            '-concurrent', experiment.concurrent.toString()
        ];

        // Ensure we create a NEW run.
        const cleanName = experiment.name.replace(/_relaunch$/, '');
        const newName = `${cleanName}_relaunch`;
        args.push('-name', newName);

        if (experiment.experiment_control) {
            args.push('-control', experiment.experiment_control);
        }

        console.log(`[Relaunch] Executing: ${cmd} ${args.join(' ')}`);

        // Spawn process
        const child = spawn(cmd, args, {
            cwd: rootDir,
            env: { ...process.env, PATH: process.env.PATH },
            stdio: 'ignore' // detach
        });

        child.unref();

        return NextResponse.json({
            message: 'Experiment relaunched',
            name: newName,
            originalId: experimentId
        });

    } catch (error) {
        console.error('Failed to relaunch experiment:', error);
        return NextResponse.json({ error: String(error) }, { status: 500 });
    }
}
