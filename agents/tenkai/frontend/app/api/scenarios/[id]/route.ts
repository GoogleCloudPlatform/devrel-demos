import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;
        const scenariosDir = path.join(process.cwd(), '..', 'scenarios');
        const scenarioDir = path.join(scenariosDir, id);
        const yamlPath = path.join(scenarioDir, 'scenario.yaml');

        if (!fs.existsSync(yamlPath)) {
            return NextResponse.json({ error: 'Scenario not found' }, { status: 404 });
        }

        const content = fs.readFileSync(yamlPath, 'utf8');

        // Simple parsing to JSON, but returning raw YAML + parsed metadata is useful
        // For now, let's return the simplified fields + raw content

        let name = id;
        let description = '';

        try {
            const nameMatch = content.match(/^name:\s*"?([^"\n]+)"?/m);
            if (nameMatch && nameMatch[1]) name = nameMatch[1];

            const descMatch = content.match(/^description:\s*"?([^"\n]+)"?/m);
            if (descMatch && descMatch[1]) description = descMatch[1];
        } catch (e) { }

        return NextResponse.json({
            id: id,
            name: name,
            description: description,
            raw: content
        });

    } catch (error) {
        console.error('Failed to get scenario:', error);
        return NextResponse.json({ error: 'Failed to get scenario' }, { status: 500 });
    }
}
