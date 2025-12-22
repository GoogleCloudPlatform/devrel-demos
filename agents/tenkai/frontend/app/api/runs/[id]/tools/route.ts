import { NextRequest, NextResponse } from 'next/server';
import { getToolUsage } from '@/lib/api';

export async function GET(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;

    if (!id) {
        return NextResponse.json({ error: 'Run ID is required' }, { status: 400 });
    }

    const tools = await getToolUsage(parseInt(id));
    return NextResponse.json(tools);
}
