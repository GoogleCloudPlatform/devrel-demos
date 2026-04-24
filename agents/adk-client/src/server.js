const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const PORT = process.env.PORT || 8080;

// Combine API server into one variable - Server base URL
const serverBaseUrl = process.env.SERVER_BASE_URL || 'http://localhost:8000';
let TARGET_HOST = 'localhost';
let TARGET_PORT = 8000;

try {
    const url = new URL(serverBaseUrl);
    TARGET_HOST = url.hostname;
    TARGET_PORT = url.port || (url.protocol === 'https:' ? 443 : 80);
} catch (e) {
    console.error('Failed to parse SERVER_BASE_URL, using defaults:', e);
}

let cachedToken = null;
let tokenExpiry = 0;

async function getIdentityToken() {
    const now = Date.now();
    if (cachedToken && now < tokenExpiry) {
        return cachedToken;
    }

    let token = null;
    const audience = process.env.SERVER_BASE_URL || 'http://localhost:8000';

    // 1. Try metadata server
    try {
        token = await new Promise((resolve, reject) => {
            const options = {
                hostname: 'metadata.google.internal',
                path: `/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(audience)}`,
                headers: {
                    'Metadata-Flavor': 'Google'
                },
                timeout: 500
            };
            const metaReq = http.get(options, (metaRes) => {
                let data = '';
                metaRes.on('data', (chunk) => data += chunk);
                metaRes.on('end', () => {
                    if (metaRes.statusCode === 200) resolve(data.trim());
                    else reject(new Error(`Status ${metaRes.statusCode}`));
                });
            });
            metaReq.on('error', (err) => reject(err));
            metaReq.on('timeout', () => {
                metaReq.destroy();
                reject(new Error('Timeout'));
            });
        });
        console.log('Successfully fetched identity token from metadata server.');
    } catch (e) {
        console.log('Metadata server not available, falling back to gcloud auth...');
        // 2. Try gcloud auth
        try {
            token = await new Promise((resolve, reject) => {
                exec('gcloud auth print-identity-token', (error, stdout, stderr) => {
                    if (error) reject(error);
                    else resolve(stdout.trim());
                });
            });
            console.log('Successfully fetched identity token from gcloud auth.');
        } catch (e2) {
            console.error('Failed to get identity token from both metadata server and gcloud auth.');
            return null;
        }
    }

    if (token) {
        cachedToken = token;
        tokenExpiry = now + 5 * 60 * 1000; // Cache for 5 minutes
    }
    return token;
}

const apiLib = serverBaseUrl.startsWith('https') ? https : http;

const server = http.createServer(async (req, res) => {
    console.log(`${req.method} ${req.url}`);

    // Serve config
    if (req.url === '/config') {
        let appName = process.env.AGENT_NAME;
        let appDescription = '';

        try {
            const token = await getIdentityToken();
            const appsResponse = await new Promise((resolve, reject) => {
                const options = {
                    hostname: TARGET_HOST,
                    port: TARGET_PORT,
                    path: '/list-apps?detailed=true',
                    method: 'GET',
                    headers: {}
                };
                if (token) {
                    options.headers['Authorization'] = `Bearer ${token}`;
                }
                const apiReq = apiLib.request(options, (apiRes) => {
                    let data = '';
                    apiRes.on('data', (chunk) => { data += chunk; });
                    apiRes.on('end', () => {
                        try {
                            resolve(JSON.parse(data));
                        } catch (e) {
                            reject(e);
                        }
                    });
                });
                apiReq.on('error', (e) => reject(e));
                apiReq.end();
            });

            const appsList = appsResponse.apps || [];

            if (!appName) {
                if (appsList.length > 0) {
                    const targetApp = appsList.find(a => a.name !== 'web_client') || appsList[0];
                    appName = targetApp.name;
                    appDescription = targetApp.description;
                } else {
                    appName = 'agent';
                }
            } else {
                const targetApp = appsList.find(a => a.name === appName);
                if (targetApp) {
                    appDescription = targetApp.description;
                }
            }
            console.log(`Config resolved: appName=${appName}, description=${appDescription}`);
        } catch (e) {
            console.error('Failed to fetch apps from API server:', e);
            if (!appName) appName = 'agent';
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ appName, description: appDescription }));
        return;
    }

    // Proxy API requests to the agent server
    if (req.url.startsWith('/run_sse') || req.url.startsWith('/run') || req.url.startsWith('/apps')) {
        const token = await getIdentityToken();
        const headers = { ...req.headers };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        delete headers['host'];
        delete headers['origin'];
        delete headers['referer'];

        const options = {
            hostname: TARGET_HOST,
            port: TARGET_PORT,
            path: req.url,
            method: req.method,
            headers: headers
        };

        const proxyReq = apiLib.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
        });

        if (req.url.startsWith('/run_sse')) {
            res.on('close', () => {
                if (!res.writableEnded) {
                    console.log(`[server.js] Client disconnected prematurely, aborting proxy request to ${options.hostname}:${options.port}`);
                    proxyReq.abort();
                }
            });
        }

        proxyReq.on('error', (e) => {
            console.error(`Problem with proxy request: ${e.message}`);
            res.writeHead(500);
            res.end('Proxy error');
        });

        req.pipe(proxyReq);
        return;
    }

    // Serve static files
    const parsedPath = req.url.split('?')[0];
    let filePath = path.join(__dirname, parsedPath === '/' ? 'index.html' : parsedPath);

    // Security check: ensure file is within __dirname
    if (!filePath.startsWith(__dirname)) {
        res.writeHead(403);
        res.end('Forbidden');
        return;
    }

    const extname = path.extname(filePath);
    let contentType = 'text/html';
    switch (extname) {
        case '.js':
            contentType = 'text/javascript';
            break;
        case '.css':
            contentType = 'text/css';
            break;
        case '.json':
            contentType = 'application/json';
            break;
        case '.png':
            contentType = 'image/png';
            break;
        case '.jpg':
            contentType = 'image/jpg';
            break;
        case '.gif':
            contentType = 'image/gif';
            break;
        case '.svg':
            contentType = 'image/svg+xml';
            break;
    }

    fs.readFile(filePath, (error, content) => {
        if (error) {
            if (error.code == 'ENOENT') {
                res.writeHead(404);
                res.end('File not found');
            } else {
                res.writeHead(500);
                res.end(`Server error: ${error.code}`);
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

server.listen(PORT, () => {
    console.log(`Client server and proxy running at http://localhost:${PORT}/`);
    console.log(`Proxying API requests to http://${TARGET_HOST}:${TARGET_PORT}/`);
});
