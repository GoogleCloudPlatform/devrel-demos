import { NextRequest, NextResponse } from 'next/server';
import { getSimplifiedMetrics } from '@/lib/api';

export async function GET(req: NextRequest) {
    const { searchParams } = new URL(req.url);
    const id = searchParams.get('id');

    if (!id) {
        return NextResponse.json({ error: 'ID is required' }, { status: 400 });
    }

    const metrics = await getSimplifiedMetrics(id);
    if (!metrics) {
        return NextResponse.json({ error: 'Metrics not found' }, { status: 404 });
    }

    return NextResponse.json(metrics);
}
