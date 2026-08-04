/**
Copyright 2026 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';
import path from 'path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const args = process.argv.slice(2);
let suite = 'unit';

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--selectProjects' || args[i] === '--suite') {
    suite = args[i + 1] || 'unit';
    break;
  }
  if (args[i].startsWith('--suite=')) {
    suite = args[i].split('=')[1];
    break;
  }
  if (args[i].startsWith('--selectProjects=')) {
    suite = args[i].split('=')[1];
    break;
  }
}

const suiteFileMap = {
  unit: 'tests/unit.test.js',
  integration: 'tests/integration.test.js',
  contract: 'tests/contract.test.js',
  security: 'tests/security.test.js'
};

const testFile = suiteFileMap[suite] || `tests/${suite}.test.js`;
const fullPath = path.join(__dirname, testFile);

console.log(`Running mock test suite: ${suite} (${testFile})...`);
const result = spawnSync('node', ['--test', fullPath], { stdio: 'inherit' });
process.exit(result.status ?? 0);
