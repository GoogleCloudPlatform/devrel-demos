import { NextRequest, NextResponse } from 'next/server';

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ text: string }> }
) {
    const { text } = await params;
    return NextResponse.json({ echo: text });
}
