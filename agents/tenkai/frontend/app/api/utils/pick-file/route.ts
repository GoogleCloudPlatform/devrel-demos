import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';
import fs from 'fs';
import { promisify } from 'util';

const execAsync = promisify(exec);

export async function GET() {
    try {
        // Trigger native Mac file picker
        // We use POSIX path of (choose file) to get the absolute path
        const { stdout, stderr } = await execAsync("osascript -e 'POSIX path of (choose file)'");

        if (stderr) {
            console.error('AppleScript Error:', stderr);
            return NextResponse.json({ error: stderr }, { status: 500 });
        }

        const absolutePath = stdout.trim();
        if (!absolutePath) {
            return NextResponse.json({ cancelled: true });
        }

        // Try to make it relative to project root if possible
        const rootDir = fs.existsSync(path.join(process.cwd(), 'scenarios')) ? process.cwd() : path.join(process.cwd(), '..');
        let finalPath = absolutePath;

        if (absolutePath.startsWith(rootDir)) {
            finalPath = path.relative(rootDir, absolutePath);
        }

        return NextResponse.json({ path: finalPath });
    } catch (error: any) {
        // Check for cancellation (exit code 1, stderr 'execution error: User cancelled. (-128)')
        if (error.code === 1 || (error.stderr && error.stderr.includes('-128'))) {
            return NextResponse.json({ cancelled: true });
        }

        console.error('Failed to pick file:', error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
