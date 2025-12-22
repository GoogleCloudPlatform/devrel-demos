import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
    try {
        const templatesDir = path.join(process.cwd(), '..', 'experiments', 'templates');
        if (!fs.existsSync(templatesDir)) {
            return NextResponse.json([]);
        }

        const entries = fs.readdirSync(templatesDir, { withFileTypes: true });

        const templates = entries
            .filter(entry => entry.isDirectory() && entry.name !== 'runs')
            .map(entry => {
                const configPath = path.join(templatesDir, entry.name, 'config.yaml');
                let name = entry.name;
                if (fs.existsSync(configPath)) {
                    try {
                        const content = fs.readFileSync(configPath, 'utf8');
                        // Simple manual parsing to avoid strict yaml dependency if possible, or use regex
                        // name: "something"
                        const match = content.match(/^name:\s*"?([^"\n]+)"?/m);
                        if (match && match[1]) {
                            name = match[1];
                        }
                    } catch (e) {
                        console.error(`Failed to parse config for ${entry.name}`, e);
                    }
                }
                return {
                    id: entry.name,
                    name: name
                };
            });

        return NextResponse.json(templates);
    } catch (error) {
        console.error('Failed to list templates:', error);
        return NextResponse.json({ error: 'Failed to list templates' }, { status: 500 });
    }
}

export async function POST(req: NextRequest) {
    try {
        const { name, description } = await req.json();

        if (!name) {
            return NextResponse.json({ error: 'Template name is required' }, { status: 400 });
        }

        const cleanName = name.toLowerCase().replace(/[^a-z0-9-_]/g, '-');
        const templatesDir = path.join(process.cwd(), '..', 'experiments', 'templates');
        const newTemplateDir = path.join(templatesDir, cleanName);

        if (fs.existsSync(newTemplateDir)) {
            return NextResponse.json({ error: 'Template already exists' }, { status: 409 });
        }

        fs.mkdirSync(newTemplateDir, { recursive: true });

        // Create initial config.yaml
        const initialConfig = `name: "${cleanName}"
description: "${description || 'New experiment template'}"
repetitions: 1
max_concurrent: 1
timeout: "5m"

alternatives:
  - name: "default"
    description: "Default Gemini configuration"
    command: "gemini"
    args: ["--output-format", "stream-json", "--yolo"]

scenarios:
  - name: "example_scenario"
`;

        fs.writeFileSync(path.join(newTemplateDir, 'config.yaml'), initialConfig);

        return NextResponse.json({ message: 'Template created', name: cleanName });
    } catch (error) {
        console.error('Failed to create template:', error);
        return NextResponse.json({ error: 'Failed to create template' }, { status: 500 });
    }
}
