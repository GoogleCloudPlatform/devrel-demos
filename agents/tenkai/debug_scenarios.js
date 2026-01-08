const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

async function getScenarios() {
    const rootDir = process.cwd();
    console.log("CWD:", rootDir);

    // Logic from api.ts
    const possiblePaths = [
        path.join(process.cwd(), 'scenarios'),
        path.join(process.cwd(), '..', 'scenarios'),
        path.join(process.cwd(), '..', '..', 'scenarios'),
        path.join(process.cwd(), 'agents/tenkai/scenarios') // Add explicit relative path check
    ];

    let scenariosDir = '';
    for (const p of possiblePaths) {
        console.log("Checking:", p);
        if (fs.existsSync(p)) {
            scenariosDir = p;
            console.log("Found scenarios at:", scenariosDir);
            break;
        }
    }

    if (!scenariosDir) {
        console.error("Scenarios directory not found");
        return [];
    }

    try {
        const entries = fs.readdirSync(scenariosDir, { withFileTypes: true });
        entries.forEach(entry => {
            if (entry.isDirectory()) {
                const yamlPath = path.join(scenariosDir, entry.name, 'scenario.yaml');
                console.log(`Checking file for ${entry.name}:`, yamlPath);

                if (fs.existsSync(yamlPath)) {
                    try {
                        const content = fs.readFileSync(yamlPath, 'utf8');
                        const data = yaml.load(content);
                        console.log(`Loaded ${entry.name}:`, { name: data.name, description: data.description });
                    } catch (e) {
                        console.error(`Failed to parse scenario config for ${entry.name}`, e);
                    }
                } else {
                    console.log(`File not found: ${yamlPath}`);
                }
            }
        });
    } catch (e) {
        console.error("Failed to read scenarios from disk", e);
    }
}

getScenarios();
