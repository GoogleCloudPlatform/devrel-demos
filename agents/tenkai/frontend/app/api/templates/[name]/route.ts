import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { getNextExperimentNumber } from '@/lib/api';

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ name: string }> }
) {
    try {
        const { name } = await params;
        const rootDir = path.join(process.cwd(), '..');
        const configPath = path.join(rootDir, 'experiments', 'templates', name, 'config.yaml');

        if (!fs.existsSync(configPath)) {
            return NextResponse.json({ error: `Template not found at ${configPath}` }, { status: 404 });
        }

        const content = fs.readFileSync(configPath, 'utf8');
        const config = yaml.load(content) as any;

        const nameBase = config.name || name;
        const nextNum = await getNextExperimentNumber(nameBase);

        return NextResponse.json({
            name: nameBase,
            suggestedName: `${nameBase}_${nextNum}`,
            config
        });
    } catch (error) {
        return NextResponse.json({ error: String(error) }, { status: 500 });
    }
}

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ name: string }> }
) {
    try {
        const { name } = await params;

        // Safety check to prevent deleting something outside templates
        if (!name || name.includes('..') || name.includes('/')) {
            return NextResponse.json({ error: 'Invalid template name' }, { status: 400 });
        }

        const rootDir = path.join(process.cwd(), '..');
        const templateDir = path.join(rootDir, 'experiments', 'templates', name);

        if (!fs.existsSync(templateDir)) {
            return NextResponse.json({ error: `Template directory not found: ${name}` }, { status: 404 });
        }

        fs.rmSync(templateDir, { recursive: true, force: true });

        return NextResponse.json({ message: 'Template deleted successfully' });
    } catch (error) {
        console.error("Delete Template Error:", error);
        return NextResponse.json({ error: String(error) }, { status: 500 });
    }
}
