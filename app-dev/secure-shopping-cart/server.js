// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

const http = require('node:http');
const https = require('node:https');
const fs = require('node:fs');
const path = require('node:path');

const PORT = process.env.PORT || 8080;
let PROJECT_ID =
  process.env.PROJECT_ID || process.env.GOOGLE_CLOUD_PROJECT || process.env.GCP_PROJECT || '';

// Base API Endpoints
const METADATA_SERVER_BASE = 'http://metadata.google.internal/computeMetadata/v1';
const FIRESTORE_API_BASE = process.env.FIRESTORE_EMULATOR_HOST
  ? `http://${process.env.FIRESTORE_EMULATOR_HOST}/v1`
  : process.env.FIRESTORE_API_BASE || 'https://firestore.googleapis.com/v1';

// Canonical Product Catalog (Authoritative source of truth for pricing)
const DEFAULT_PRODUCTS = [
  { id: 'prod_honey', name: 'Raw Clover Honey', price: 14.5, icon: '🍯', category: 'Pantry' },
  {
    id: 'prod_figs',
    name: 'Organic Black Mission Figs',
    price: 8.0,
    icon: '🫐',
    category: 'Produce',
  },
  { id: 'prod_bread', name: 'Artisan Sourdough Loaf', price: 9.25, icon: '🥖', category: 'Bakery' },
  { id: 'prod_greens', name: 'Heirloom Baby Greens', price: 6.5, icon: '🥬', category: 'Produce' },
  {
    id: 'prod_olive_oil',
    name: 'Cold-Pressed Olive Oil',
    price: 18.0,
    icon: '🫒',
    category: 'Pantry',
  },
  {
    id: 'prod_cheese',
    name: 'Aged Farmhouse Cheddar',
    price: 11.75,
    icon: '🧀',
    category: 'Dairy',
  },
  {
    id: 'prod_coffee',
    name: 'Single-Origin Coffee',
    price: 16.5,
    icon: '☕',
    category: 'Beverage',
  },
  {
    id: 'prod_chocolate',
    name: 'Dark Chocolate Truffles',
    price: 12.0,
    icon: '🍫',
    category: 'Confection',
  },
];

let cachedToken = null;
let tokenExpiresAt = 0;

// Discover Google Cloud Project ID from environment or GCE Metadata Server
async function getGcpProjectId() {
  if (PROJECT_ID) return PROJECT_ID;

  return new Promise((resolve) => {
    const req = http.request(
      `${METADATA_SERVER_BASE}/project/project-id`,
      {
        headers: { 'Metadata-Flavor': 'Google' },
        timeout: 2000,
      },
      (res) => {
        let rawData = '';
        res.on('data', (chunk) => (rawData += chunk));
        res.on('end', () => {
          if (res.statusCode === 200 && rawData.trim()) {
            PROJECT_ID = rawData.trim();
            resolve(PROJECT_ID);
          } else {
            resolve(PROJECT_ID || 'gcp-project');
          }
        });
      },
    );

    req.on('error', () => resolve(PROJECT_ID || 'gcp-project'));
    req.on('timeout', () => {
      req.destroy();
      resolve(PROJECT_ID || 'gcp-project');
    });
    req.end();
  });
}

// Fetch Google Cloud IAM Service Account Access Token from Metadata Server
async function getGcpAccessToken() {
  const now = Date.now();
  if (cachedToken && now < tokenExpiresAt - 60000) {
    return cachedToken;
  }

  return new Promise((resolve) => {
    const req = http.request(
      `${METADATA_SERVER_BASE}/instance/service-accounts/default/token`,
      {
        headers: { 'Metadata-Flavor': 'Google' },
        timeout: 2500,
      },
      (res) => {
        let rawData = '';
        res.on('data', (chunk) => (rawData += chunk));
        res.on('end', () => {
          if (res.statusCode === 200) {
            try {
              const data = JSON.parse(rawData);
              cachedToken = data.access_token;
              tokenExpiresAt = Date.now() + data.expires_in * 1000;
              resolve(cachedToken);
            } catch {
              resolve(null);
            }
          } else {
            resolve(null);
          }
        });
      },
    );

    req.on('error', () => resolve(null));
    req.on('timeout', () => {
      req.destroy();
      resolve(null);
    });
    req.end();
  });
}

// Write document to Cloud Firestore via REST API using IAM Admin privileges
async function writeFirestoreDocument(collection, docId, fields) {
  const token = await getGcpAccessToken();
  const projectId = await getGcpProjectId();
  if (!token) return { success: false, reason: 'No IAM token available' };

  const client = FIRESTORE_API_BASE.startsWith('https:') ? https : http;

  return new Promise((resolve) => {
    const url = `${FIRESTORE_API_BASE}/projects/${projectId}/databases/(default)/documents/${collection}?documentId=${docId}`;
    const payload = JSON.stringify({ fields });

    const req = client.request(
      url,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload),
        },
        timeout: 5000,
      },
      (res) => {
        let responseData = '';
        res.on('data', (c) => (responseData += c));
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve({ success: true });
          } else if (res.statusCode === 409) {
            // Document already exists -> PATCH
            const patchUrl = `${FIRESTORE_API_BASE}/projects/${projectId}/databases/(default)/documents/${collection}/${docId}`;
            const patchReq = client.request(
              patchUrl,
              {
                method: 'PATCH',
                headers: {
                  Authorization: `Bearer ${token}`,
                  'Content-Type': 'application/json',
                  'Content-Length': Buffer.byteLength(payload),
                },
              },
              (patchRes) => {
                patchRes.resume();
                resolve({ success: patchRes.statusCode >= 200 && patchRes.statusCode < 300 });
              },
            );
            patchReq.on('error', () => resolve({ success: false }));
            patchReq.write(payload);
            patchReq.end();
          } else {
            resolve({ success: false, status: res.statusCode, body: responseData });
          }
        });
      },
    );

    req.on('error', (err) => resolve({ success: false, error: err.message }));
    req.write(payload);
    req.end();
  });
}

// Clear user's cart subcollection in Firestore upon successful checkout
async function clearUserCart(uid) {
  const token = await getGcpAccessToken();
  const projectId = await getGcpProjectId();
  if (!token) return;

  const client = FIRESTORE_API_BASE.startsWith('https:') ? https : http;

  return new Promise((resolve) => {
    const listUrl = `${FIRESTORE_API_BASE}/projects/${projectId}/databases/(default)/documents/carts/${uid}/items`;
    client
      .get(listUrl, { headers: { Authorization: `Bearer ${token}` } }, (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try {
            const parsed = JSON.parse(data);
            if (parsed.documents && Array.isArray(parsed.documents)) {
              const deletePromises = parsed.documents.map((doc) => {
                return new Promise((deleteResolve) => {
                  const docName = doc.name;
                  const delUrl = docName.startsWith('http')
                    ? docName
                    : `${FIRESTORE_API_BASE}/${docName}`;
                  const delReq = client.request(
                    delUrl,
                    { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } },
                    (delRes) => {
                      delRes.resume();
                      deleteResolve();
                    },
                  );
                  delReq.on('error', () => deleteResolve());
                  delReq.end();
                });
              });
              Promise.all(deletePromises)
                .then(() => resolve())
                .catch(() => resolve());
            } else {
              resolve();
            }
          } catch {
            resolve();
          }
        });
      })
      .on('error', () => resolve());
  });
}

// Seed product catalog into Firestore on startup if needed
async function seedProducts() {
  const token = await getGcpAccessToken();
  if (!token) return;

  for (const p of DEFAULT_PRODUCTS) {
    await writeFirestoreDocument('products', p.id, {
      id: { stringValue: p.id },
      name: { stringValue: p.name },
      price: { doubleValue: p.price },
      icon: { stringValue: p.icon },
      category: { stringValue: p.category },
    });
  }
}

// HTTP Server
const server = http.createServer(async (req, res) => {
  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;

  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // --- API: GET /api/config ---
  if (pathname === '/api/config' && req.method === 'GET') {
    const projectId = await getGcpProjectId();
    const apiKey = process.env.FIREBASE_API_KEY || process.env.WEB_API_KEY || '';
    const appId = process.env.FIREBASE_APP_ID || '';
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        projectId: projectId,
        authDomain: `${projectId}.firebaseapp.com`,
        storageBucket: `${projectId}.appspot.com`,
        apiKey: apiKey,
        appId: appId,
        nodeVersion: process.version,
      }),
    );
    return;
  }

  // --- API: GET /api/products ---
  if (pathname === '/api/products' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        source: 'Google Cloud Firestore (/products)',
        products: DEFAULT_PRODUCTS,
        count: DEFAULT_PRODUCTS.length,
      }),
    );
    return;
  }

  // --- API: POST /api/checkout (Server Price Authority) ---
  if (pathname === '/api/checkout' && req.method === 'POST') {
    let body = '';
    req.on('data', (chunk) => (body += chunk));
    req.on('end', async () => {
      const startTime = Date.now();
      try {
        const payload = JSON.parse(body || '{}');
        const uid = payload.uid || 'anon_visitor';
        const items = payload.items || {};

        const itemKeys = Object.keys(items);
        if (itemKeys.length === 0) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Cart is empty.' }));
          return;
        }

        // Server-Side Price Verification (Catalog Authority)
        let totalAmount = 0;
        const verifiedLines = [];

        for (const pid of itemKeys) {
          const product = DEFAULT_PRODUCTS.find((p) => p.id === pid);
          if (!product) continue;

          const rawQty = items[pid]?.qty || items[pid] || 1;
          const qty = Math.max(1, Math.min(99, parseInt(rawQty, 10) || 1));
          const lineTotal = product.price * qty;
          totalAmount += lineTotal;

          verifiedLines.push({
            productId: pid,
            name: product.name,
            unitPrice: product.price,
            qty: qty,
            lineTotal: parseFloat(lineTotal.toFixed(2)),
          });
        }

        const finalTotal = parseFloat(totalAmount.toFixed(2));
        const orderId = `ord_${Math.random().toString(36).substring(2, 9)}`;
        const timestamp = new Date().toISOString();

        // Convert verifiedLines into Firestore REST array format
        const linesArray = verifiedLines.map((line) => ({
          mapValue: {
            fields: {
              productId: { stringValue: line.productId },
              name: { stringValue: line.name },
              unitPrice: { doubleValue: line.unitPrice },
              qty: { integerValue: line.qty.toString() },
              lineTotal: { doubleValue: line.lineTotal },
            },
          },
        }));

        // Write verified order to Firestore (/orders/{orderId})
        const firestoreFields = {
          orderId: { stringValue: orderId },
          ownerUid: { stringValue: uid },
          total: { doubleValue: finalTotal },
          status: { stringValue: 'PAID_VERIFIED' },
          createdAt: { timestampValue: timestamp },
          itemCount: { integerValue: verifiedLines.length.toString() },
          lines: { arrayValue: { values: linesArray } },
        };

        const dbResult = await writeFirestoreDocument('orders', orderId, firestoreFields);

        // Clear the user's cart in Firestore
        await clearUserCart(uid);

        const latencyMs = Date.now() - startTime;

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({
            success: true,
            order: {
              orderId,
              ownerUid: uid,
              total: finalTotal,
              lines: verifiedLines,
              status: 'PAID_VERIFIED',
              timestamp: new Date().toLocaleTimeString(),
            },
            firestoreSync: dbResult.success,
            latencyMs,
            serverMode: 'Cloud Run Firebase Admin Authority',
          }),
        );
      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });
    return;
  }

  // --- STATIC FILE SERVING ---
  let filePath = path.join(__dirname, 'public', 'index.html');
  if (pathname !== '/' && pathname !== '/index.html') {
    const candidatePublic = path.join(__dirname, 'public', pathname);
    const candidateRoot = path.join(__dirname, pathname);
    if (fs.existsSync(candidatePublic) && fs.statSync(candidatePublic).isFile()) {
      filePath = candidatePublic;
    } else if (fs.existsSync(candidateRoot) && fs.statSync(candidateRoot).isFile()) {
      filePath = candidateRoot;
    }
  }

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
    } else {
      const ext = path.extname(filePath).toLowerCase();
      let contentType = 'text/html';
      if (ext === '.js') contentType = 'application/javascript';
      if (ext === '.css') contentType = 'text/css';
      if (ext === '.json') contentType = 'application/json';
      if (ext === '.png') contentType = 'image/png';
      if (ext === '.jpg' || ext === '.jpeg') contentType = 'image/jpeg';
      res.writeHead(200, { 'Content-Type': contentType });
      res.end(content);
    }
  });
});

server.listen(PORT, async () => {
  const projectId = await getGcpProjectId();
  console.log(`Shopping Cart Server running on port ${PORT} (GCP Project: ${projectId})`);
  seedProducts().catch(console.error);
});
