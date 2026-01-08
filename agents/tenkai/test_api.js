const fs = require('fs');
const path = require('path');

function getTemplates() {
    try {
        const templatesDir = path.join(process.cwd(), 'experiments', 'templates');
        console.log("Checking templates directory:", templatesDir);
        if (!fs.existsSync(templatesDir)) {
            console.log("Directory does not exist");
            return [];
        }

        const entries = fs.readdirSync(templatesDir, { withFileTypes: true });
        const templates = entries
            .filter(entry => entry.isDirectory() && entry.name !== 'runs')
            .map(entry => {
                const configPath = path.join(templatesDir, entry.name, 'config.yaml');
                let name = entry.name;
                if (fs.existsSync(configPath)) {
                    const content = fs.readFileSync(configPath, 'utf8');
                    const match = content.match(/^name:\s*"?([^"\n]+)"?/m);
                    if (match && match[1]) {
                        name = match[1];
                    }
                }
                return { id: entry.name, name: name };
            });
        return templates;
    } catch (error) {
        console.error('Failed to list templates:', error);
        return [];
    }
}

function getScenarios() {
    try {
        const scenariosDir = path.join(process.cwd(), 'scenarios');
        console.log("Checking scenarios directory:", scenariosDir);
        if (!fs.existsSync(scenariosDir)) {
            console.log("Directory does not exist");
            return [];
        }

        const entries = fs.readdirSync(scenariosDir, { withFileTypes: true });
        const scenarios = entries
            .filter(entry => entry.isDirectory())
            .map(entry => {
                const yamlPath = path.join(scenariosDir, entry.name, 'scenario.yaml');
                let name = entry.name;
                let description = '';
                if (fs.existsSync(yamlPath)) {
                    const content = fs.readFileSync(yamlPath, 'utf8');
                    const nameMatch = content.match(/^name:\s*"?([^"\n]+)"?/m);
                    if (nameMatch && nameMatch[1]) name = nameMatch[1];
                    const descMatch = content.match(/^description:\s*"?([^"\n]+)"?/m);
                    if (descMatch && descMatch[1]) description = descMatch[1];
                }
                return { id: entry.name, name: name, description: description };
            });
        return scenarios;
    } catch (error) {
        console.error('Failed to list scenarios:', error);
        return [];
    }
}

console.log("Templates:", getTemplates());
console.log("Scenarios:", getScenarios());
