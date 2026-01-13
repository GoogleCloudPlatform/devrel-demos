const fs = require('fs');
const yaml = require('js-yaml');
const path = require('path');

const scenarioPath = 'scenarios/1768294561159150000/scenario.yaml';
const outputPath = 'scenarios/1768294561159150000/elvira.jpeg';

try {
    const fileContents = fs.readFileSync(scenarioPath, 'utf8');
    const data = yaml.load(fileContents);

    if (data.assets && data.assets.length > 0) {
        const asset = data.assets[0];
        if (asset.content instanceof Buffer || typeof asset.content === 'object') {
            // js-yaml loads !!binary as a Buffer
            fs.writeFileSync(outputPath, asset.content);
            console.log(`Successfully wrote binary content to ${outputPath}`);
            
            // Update the YAML structure
            delete asset.content;
            asset.source = 'elvira.jpeg';
            
            const newYaml = yaml.dump(data, { lineWidth: -1 });
            fs.writeFileSync(scenarioPath, newYaml);
            console.log(`Successfully updated ${scenarioPath}`);
        } else {
            console.error('Asset content is not binary or already processed');
        }
    }
} catch (e) {
    console.error(e);
}
