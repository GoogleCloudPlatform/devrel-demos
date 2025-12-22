import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ name: string }> }
) {
    try {
        const { name } = await params;
        const templatesDir = path.join(process.cwd(), '..', 'experiments', 'templates');
        const configPath = path.join(templatesDir, name, 'config.yaml');

        if (!fs.existsSync(configPath)) {
            return NextResponse.json({ error: 'Template not found' }, { status: 404 });
        }

        const content = fs.readFileSync(configPath, 'utf-8');
        // Parse basic details for suggestion
        // This is a naive parse, ideally use a yaml parser if needed struct
        const match = content.match(/name: "(.+?)"/);
        const suggestedName = match ? match[1] : name;

        return NextResponse.json({ content, suggestedName });
    } catch (error) {
        return NextResponse.json({ error: 'Failed to load template' }, { status: 500 });
    }
}

export async function POST(
    req: NextRequest,
    { params }: { params: Promise<{ name: string }> }
) {
    try {
        const { name } = await params;
        const { content } = await req.json();

        if (!content) {
            return NextResponse.json({ error: 'Content is required' }, { status: 400 });
        }

        const templatesDir = path.join(process.cwd(), '..', 'experiments', 'templates');
        const configPath = path.join(templatesDir, name, 'config.yaml');

        if (!fs.existsSync(path.dirname(configPath))) {
            return NextResponse.json({ error: 'Template not found' }, { status: 404 });
        }

        fs.writeFileSync(configPath, content);

        return NextResponse.json({ message: 'Configuration saved' });
    } catch (error) {
        console.error('Failed to save config:', error);
        return NextResponse.json({ error: 'Failed to save config' }, { status: 500 });
    }
}
