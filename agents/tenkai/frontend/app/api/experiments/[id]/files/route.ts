import { NextRequest, NextResponse } from 'next/server';
import { getConfigFile } from '@/lib/api';

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;
        const { searchParams } = new URL(req.url);
        const path = searchParams.get('path');

        if (!path) {
            return NextResponse.json({ error: 'Path is required' }, { status: 400 });
        }

        const content = await getConfigFile(id, path);

        if (content === null) {
            return NextResponse.json({ error: 'File not found' }, { status: 404 });
        }

        return NextResponse.json({ content });
    } catch (error) {
        console.error('Failed to fetch config file:', error);
        return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
    }
}
