import { NextRequest, NextResponse } from 'next/server';
import { getCheckpoint } from '@/lib/api';

export async function GET(req: NextRequest) {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get('id');

    if (!id) {
        return NextResponse.json({ error: 'ID is required' }, { status: 400 });
    }

    const checkpoint = await getCheckpoint(id);
    if (!checkpoint) {
        return NextResponse.json({ error: 'Checkpoint not found' }, { status: 404 });
    }

    return NextResponse.json(checkpoint);
}
