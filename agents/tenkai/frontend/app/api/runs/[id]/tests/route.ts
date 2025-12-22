import { NextRequest, NextResponse } from 'next/server';
import { getTestResults } from '@/lib/api';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const { id } = await params;
    try {
        const tests = await getTestResults(Number(id));
        return NextResponse.json(tests);
    } catch (error) {
        return NextResponse.json({ error: 'Failed to fetch test results' }, { status: 500 });
    }
}
