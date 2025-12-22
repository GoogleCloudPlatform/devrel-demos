import { NextRequest, NextResponse } from 'next/server';
import { getRunFiles } from '@/lib/api';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const { id } = await params;
    try {
        const files = await getRunFiles(Number(id));
        return NextResponse.json(files);
    } catch (error) {
        return NextResponse.json({ error: 'Failed to fetch run files' }, { status: 500 });
    }
}
