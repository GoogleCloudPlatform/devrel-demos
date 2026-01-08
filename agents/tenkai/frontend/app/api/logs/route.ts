import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
    try {
        // Attempt to find tenkai.log in the project root
        // Assuming Next.js is running in frontend/ or root.
        // If running in frontend/, root is ../

        // Check multiple possible locations
        const possiblePaths = [
            path.join(process.cwd(), 'tenkai.log'),
            path.join(process.cwd(), '..', 'tenkai.log'),
        ];

        let logPath = '';
        for (const p of possiblePaths) {
            if (fs.existsSync(p)) {
                logPath = p;
                break;
            }
        }

        if (!logPath) {
            return NextResponse.json({ error: 'Log file not found' }, { status: 404 });
        }

        // Read the last 1000 lines or 50KB to avoid sending too much
        // For simplicity, read whole file but limit output size
        const stat = fs.statSync(logPath);
        const fileSize = stat.size;
        const maxBytes = 100 * 1024; // 100KB

        let start = 0;
        if (fileSize > maxBytes) {
            start = fileSize - maxBytes;
        }
        const stream = fs.createReadStream(logPath, { start, encoding: 'utf8' });

        // We can return a stream directly
        // @ts-expect-error stream type mismatch
        return new NextResponse(stream, {
            headers: {
                'Content-Type': 'text/plain',
            },
        });


    } catch (error) {
        console.error('Failed to read log file:', error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
