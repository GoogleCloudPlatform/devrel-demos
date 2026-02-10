#!/usr/bin/env node

/**
 * latest-software-versions/scripts/latest.js
 * 
 * Fetches the latest stable version of a package from official registries.
 * Usage: node latest.js <ecosystem> <package_name>
 * 
 * Ecosystems: npm, pypi, go, cargo, gem
 */

const https = require('https');

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("Usage: node latest.js <ecosystem> <package_name>");
  console.error("Supported: npm, pypi, go, maven, cargo, gem, docker");
  process.exit(1);
}

const [ecosystem, pkg] = args;

function fetchJSON(url, parseJson = true) {
  return new Promise((resolve, reject) => {
    https.get(url, { headers: { 'User-Agent': 'Gemini-CLI-Version-Checker' } }, (res) => {
      let data = '';
      if (res.statusCode >= 400) {
        reject(new Error(`Registry returned ${res.statusCode}`));
        return;
      }
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          if (parseJson) {
            resolve(JSON.parse(data));
          } else {
            resolve(data);
          }
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

async function getLatest() {
  try {
    switch (ecosystem.toLowerCase()) {
            case 'npm':
        const npmData = await fetchJSON(`https://registry.npmjs.org/${pkg}`);
        const npmLatest = npmData['dist-tags']?.latest;
        if (!npmLatest) throw new Error("No latest tag found");
        
        console.log(`npm: ${pkg} @ ${npmLatest}`);
        
        const npmVerData = npmData.versions[npmLatest];
        if (npmVerData.deprecated) {
            console.log(`⚠️  WARNING: This package is deprecated! Reason: "${npmVerData.deprecated}"`);
        }
        break;

      case 'pypi':
        const pypiData = await fetchJSON(`https://pypi.org/pypi/${pkg}/json`);
        const pypiLatest = pypiData.info.version;
        console.log(`pypi: ${pkg} @ ${pypiLatest}`);
        
        if (pypiData.info.yanked) {
             console.log(`⚠️  WARNING: This release was YANKED. Reason: "${pypiData.info.yanked_reason}"`);
        }
        // PyPI doesn't have a standard "deprecated" field for the whole package, 
        // but checking for "Development Status :: 7 - Inactive" classifier is a good heuristic.
        if (pypiData.info.classifiers && pypiData.info.classifiers.includes("Development Status :: 7 - Inactive")) {
            console.log("⚠️  WARNING: This package is marked as Inactive.");
        }
        break;


                  case 'go':
        // Go proxy requires lowercase
        const goData = await fetchJSON(`https://proxy.golang.org/${pkg.toLowerCase()}/@latest`);
        console.log(`go: ${pkg} @ ${goData.Version}`);

        if (goData.Retracted) {
            console.log(`⚠️  WARNING: This version (${goData.Version}) is RETRACTED!`);
        }
        
        // Optional: Check GitHub for archived status or README warnings
        if (pkg.startsWith("github.com/")) {
            const repoPath = pkg.replace("github.com/", "");
            try {
                const repoData = await fetchJSON(`https://api.github.com/repos/${repoPath}`);
                if (repoData) {
                    if (repoData.archived) {
                        console.log(`⚠️  WARNING: GitHub repository '${repoPath}' is ARCHIVED.`);
                        return;
                    } 
                    
                    const desc = (repoData.description || "").toLowerCase();
                    if (desc.includes("deprecated") || desc.includes("moved to")) {
                        console.log(`⚠️  WARNING: Potential deprecation/move detected in description: "${repoData.description}"`);
                        return;
                    }

                    // Deep check: Check README for "deprecated"
                    const readmeData = await fetchJSON(`https://api.github.com/repos/${repoPath}/readme`);
                    if (readmeData && readmeData.content) {
                        const content = Buffer.from(readmeData.content, 'base64').toString('utf8').toLowerCase();
                        if (content.includes("deprecated") || content.includes("use google.golang.org/genai")) {
                            console.log(`⚠️  WARNING: The README for '${repoPath}' indicates this package is DEPRECATED or superseded.`);
                        }
                    }
                }
            } catch (e) {
                // Ignore GitHub API errors
            }
        }
        break;



      case 'cargo':
        const cargoData = await fetchJSON(`https://crates.io/api/v1/crates/${pkg}`);
        console.log(`cargo: ${pkg} @ ${cargoData.crate.max_stable_version}`);
        break;
      
            case 'gem':
        const gemData = await fetchJSON(`https://rubygems.org/api/v1/versions/${pkg}/latest.json`);
        console.log(`gem: ${pkg} @ ${gemData.version}`);
        break;

                                    case 'gemini':
        // Fetch from multiple official documentation sources to get the most complete picture.
        const sources = [
          'https://ai.google.dev/gemini-api/docs/models.md.txt',
          'https://ai.google.dev/gemini-api/docs/image-generation.md.txt'
        ];
        
        let allModels = [];
        let brandNames = {};

        for (const url of sources) {
            const text = await fetchJSON(url, false);
            
            // 1. Extract model codes: `gemini-1.5-flash`
            const codeMatch = text.match(/`gemini-[^`]+`/gi);
            if (codeMatch) {
                allModels.push(...codeMatch.map(m => m.replace(/`/g, '')));
            }

                                    // 2. Extract brand names dynamically
            // Pattern: - **Brand Name** : The [Model Name](url) model (`model-id`)
            // OR broader heuristic: look for "**Name** : ... (`id`)" lines
            const brandMatches = text.matchAll(/-\s+\*\*(.*?)\*\*\s+:\s+.*?`([^`]+)`/g);
            for (const match of brandMatches) {
                const brand = match[1].trim(); // e.g. "Nano Banana"
                const modelId = match[2].trim(); // e.g. "gemini-2.5-flash-image"
                brandNames[brand] = modelId;
            }


        }

        const uniqueModels = [...new Set(allModels)].sort((a, b) => {
            const va = a.match(/\d+(\.\d+)?/)?.[0] || '0';
            const vb = b.match(/\d+(\.\d+)?/)?.[0] || '0';
            return parseFloat(vb) - parseFloat(va);
        });

                        const target = pkg.toLowerCase().replace(/\s+/g, '');
        
        // Find all brands that match the target (normalized)
        const matchingBrands = Object.keys(brandNames).filter(b => 
            b.toLowerCase().replace(/\s+/g, '').includes(target)
        );
        
        if (matchingBrands.length > 0) {
            matchingBrands.forEach(brand => {
                console.log(`gemini: ${brand} (Brand Name) @ ${brandNames[brand]}`);
            });
            return;
        }



        let results = uniqueModels;
        if (target !== 'latest' && target !== 'all') {
            results = uniqueModels.filter(m => m.includes(target));
        }

        if (results.length > 0) {
            console.log(`gemini: ${pkg} @ ${results[0]}`);
            if (results.length > 1) {
                console.log(`Note: Also found ${results.slice(1, 5).join(', ')}`);
            }
        } else {
            console.log(`gemini: No models found matching "${pkg}".`);
            console.log(`Known brands: ${Object.keys(brandNames).join(', ')}`);
            console.log(`Latest codes: ${uniqueModels.slice(0, 3).join(', ')}`);
        }
        break;




      default:

        console.error(`Unknown ecosystem: ${ecosystem}`);

        console.error("Try: npm, pypi, go, cargo, gem");
        process.exit(1);
    }
  } catch (err) {
    console.error(`Error fetching version for ${pkg}: ${err.message}`);
    process.exit(1);
  }
}

getLatest();
