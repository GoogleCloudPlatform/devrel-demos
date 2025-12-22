import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
    try {
        const scenariosDir = path.join(process.cwd(), '..', 'scenarios');
        if (!fs.existsSync(scenariosDir)) {
            return NextResponse.json([]);
        }

        const entries = fs.readdirSync(scenariosDir, { withFileTypes: true });

        const scenarios = entries
            .filter(entry => entry.isDirectory())
            .map(entry => {
                const yamlPath = path.join(scenariosDir, entry.name, 'scenario.yaml');
                let name = entry.name;
                let description = '';

                if (fs.existsSync(yamlPath)) {
                    try {
                        const content = fs.readFileSync(yamlPath, 'utf8');
                        const nameMatch = content.match(/^name:\s*"?([^"\n]+)"?/m);
                        if (nameMatch && nameMatch[1]) name = nameMatch[1];

                        const descMatch = content.match(/^description:\s*"?([^"\n]+)"?/m);
                        if (descMatch && descMatch[1]) description = descMatch[1];
                    } catch (e) {
                        console.error(`Failed to parse scenario yaml for ${entry.name}`, e);
                    }
                }
                return {
                    id: entry.name, // Directory name as ID
                    name: name,
                    description: description
                };
            });

        return NextResponse.json(scenarios);
    } catch (error) {
        console.error('Failed to list scenarios:', error);
        return NextResponse.json({ error: 'Failed to list scenarios' }, { status: 500 });
    }
}
