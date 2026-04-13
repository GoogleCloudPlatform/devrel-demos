const http = require('http');
const fs = require('fs');
const path = require('path');

// Load .env file if it exists
try {
    const envPath = path.join(__dirname, '..', '.env');
    if (fs.existsSync(envPath)) {
        const envData = fs.readFileSync(envPath, 'utf-8');
        envData.split('\n').forEach(line => {
            const trimmedLine = line.trim();
            if (trimmedLine && !trimmedLine.startsWith('#')) {
                const [key, ...valueParts] = trimmedLine.split('=');
                const value = valueParts.join('='); // Handle values containing '='
                if (key && value) {
                    process.env[key.trim()] = value.trim();
                }
            }
        });
    }
} catch (e) {
    console.error('Error loading .env file:', e);
}

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

const server = http.createServer(async (req, res) => {
    console.log(`${req.method} ${req.url}`);

    // Serve config
    if (req.url === '/config') {
        let appName = process.env.AGENT_NAME;
        if (!appName) {
            try {
                const apps = await new Promise((resolve, reject) => {
                    const options = {
                        hostname: TARGET_HOST,
                        port: TARGET_PORT,
                        path: '/list-apps',
                        method: 'GET'
                    };
                    const apiReq = http.request(options, (apiRes) => {
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

                if (apps && apps.length > 0) {
                    appName = apps.find(a => a !== 'web_client') || apps[0];
                } else {
                    appName = 'agent';
                }
                console.log(`Auto-detected appName: ${appName} from ${JSON.stringify(apps)}`);
            } catch (e) {
                console.error('Failed to fetch apps from API server:', e);
                appName = 'agent';
            }
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ appName }));
        return;
    }

    // Proxy API requests to the agent server
    if (req.url.startsWith('/run_sse') || req.url.startsWith('/run') || req.url.startsWith('/apps')) {
        const options = {
            hostname: TARGET_HOST,
            port: TARGET_PORT,
            path: req.url,
            method: req.method,
            headers: req.headers
        };

        // Avoid CORS issues by removing origin headers if necessary,
        // or let them pass if target handles them.
        // We keep them to be transparent.

        const proxyReq = http.request(options, (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
        });

        proxyReq.on('error', (e) => {
            console.error(`Problem with proxy request: ${e.message}`);
            res.writeHead(500);
            res.end('Proxy error');
        });

        req.pipe(proxyReq);
        return;
    }

    // Serve static files
    let filePath = path.join(__dirname, req.url === '/' ? 'index.html' : req.url);

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
