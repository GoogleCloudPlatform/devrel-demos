import { NextRequest, NextResponse } from 'next/server';
import { getLintResults } from '@/lib/api';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const { id } = await params;
    try {
        const lint = await getLintResults(Number(id));
        return NextResponse.json(lint);
    } catch (error) {
        return NextResponse.json({ error: 'Failed to fetch lint results' }, { status: 500 });
    }
}
