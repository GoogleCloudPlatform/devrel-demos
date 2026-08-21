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

const { describe, it, before } = require('node:test');
const assert = require('node:assert/strict');

// Dynamic test URL: set APP_URL or CLOUD_RUN_URL to test a remote deployment,
// or defaults to local development server (http://localhost:8080).
const APP_URL = process.env.APP_URL || process.env.CLOUD_RUN_URL || 'http://localhost:8080';

// Canonical Catalog
const DEFAULT_PRODUCTS = [
  { id: 'prod_honey', name: 'Raw Clover Honey', price: 14.5, category: 'Pantry' },
  { id: 'prod_figs', name: 'Organic Black Mission Figs', price: 8.0, category: 'Produce' },
  { id: 'prod_bread', name: 'Artisan Sourdough Loaf', price: 9.25, category: 'Bakery' },
  { id: 'prod_greens', name: 'Heirloom Baby Greens', price: 6.5, category: 'Produce' },
  { id: 'prod_olive_oil', name: 'Cold-Pressed Olive Oil', price: 18.0, category: 'Pantry' },
  { id: 'prod_cheese', name: 'Aged Farmhouse Cheddar', price: 11.75, category: 'Dairy' },
  { id: 'prod_coffee', name: 'Single-Origin Coffee', price: 16.5, category: 'Beverage' },
  { id: 'prod_chocolate', name: 'Dark Chocolate Truffles', price: 12.0, category: 'Confection' },
];

// ==============================================================================
// 1. FIRESTORE SECURITY RULES EVALUATOR (JavaScript Mirror)
// ==============================================================================
function evaluateCartWrite(authUid, pathUid, data) {
  if (!authUid) return { allowed: false, error: 'Unauthenticated' };
  if (authUid !== pathUid) return { allowed: false, error: 'Path UID mismatch' };
  if (!data || typeof data !== 'object') return { allowed: false, error: 'Invalid data' };

  const keys = Object.keys(data);
  const hasOnlyQty = keys.length === 1 && keys[0] === 'qty';
  if (!hasOnlyQty) return { allowed: false, error: 'Keys must only contain qty' };

  const qty = data.qty;
  if (!Number.isInteger(qty)) return { allowed: false, error: 'Qty must be integer' };
  if (qty < 1 || qty > 99) return { allowed: false, error: 'Qty must be between 1 and 99' };

  return { allowed: true };
}

function evaluateCartDelete(authUid, pathUid) {
  if (!authUid) return { allowed: false, error: 'Unauthenticated' };
  if (authUid !== pathUid) return { allowed: false, error: 'Path UID mismatch' };
  return { allowed: true };
}

function evaluateProductAccess(operation, isAdmin = false) {
  if (operation === 'read') return { allowed: true };
  if (operation === 'write') {
    if (isAdmin) return { allowed: true };
    return { allowed: false, error: 'Client writes forbidden' };
  }
  return { allowed: false, error: 'Unknown operation' };
}

function evaluateOrdersRead(authUid, queryFilterOwnerUid, docOwnerUid) {
  if (!authUid) return { allowed: false, error: 'Unauthenticated' };
  if (queryFilterOwnerUid !== authUid) return { allowed: false, error: 'Unscoped query' };
  if (authUid !== docOwnerUid) return { allowed: false, error: 'Owner mismatch' };
  return { allowed: true };
}

function evaluateOrdersWrite(isAdmin = false) {
  if (isAdmin) return { allowed: true };
  return { allowed: false, error: 'Client writes strictly forbidden' };
}

// ==============================================================================
// 2. SERVER CHECKOUT ENGINE (JavaScript Mirror)
// ==============================================================================
function calculateServerOrder(uid, items) {
  const itemKeys = Object.keys(items || {});
  if (itemKeys.length === 0) return { status: 400, error: 'Cart is empty.' };

  let totalAmount = 0;
  const verifiedLines = [];

  for (const pid of itemKeys) {
    const product = DEFAULT_PRODUCTS.find((p) => p.id === pid);
    if (!product) continue;

    const raw = items[pid];
    const rawQty = typeof raw === 'object' && raw !== null ? raw.qty : raw;
    const parsedQty = parseInt(rawQty, 10);
    const qty = Math.max(1, Math.min(99, Number.isNaN(parsedQty) ? 1 : parsedQty));
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

  return {
    status: 200,
    order: {
      orderId,
      ownerUid: uid,
      total: finalTotal,
      lines: verifiedLines,
      status: 'PAID_VERIFIED',
    },
  };
}

// ==============================================================================
// 3. CART MIGRATION & AUTHENTICATION FLOW ENGINE (JavaScript Mirror)
// ==============================================================================
function migrateGuestCart(guestUid, returningUid, guestCart, returningUserCart) {
  if (guestUid === returningUid) return { ...returningUserCart };
  const merged = { ...returningUserCart };

  for (const [pid, data] of Object.entries(guestCart || {})) {
    const guestQty =
      typeof data === 'object' && data !== null ? data.qty || 1 : parseInt(data, 10) || 1;
    const existingQty = merged[pid] ? merged[pid].qty : 0;
    const safeGuestQty = Number.isNaN(guestQty) || guestQty < 1 ? 1 : guestQty;
    const safeExistingQty = Number.isNaN(existingQty) ? 0 : existingQty;
    const finalQty = Math.max(1, Math.min(99, safeExistingQty + safeGuestQty));
    merged[pid] = { qty: finalQty };
  }
  return merged;
}

function resolveGoogleAuthAction(isAnonymous, currentUserUid, targetUserUid) {
  if (isAnonymous && currentUserUid) {
    if (!targetUserUid || targetUserUid === currentUserUid) {
      return { action: 'LINK_IN_PLACE', requiresMigration: false, targetUid: currentUserUid };
    }
    return { action: 'MIGRATE_AND_SWITCH', requiresMigration: true, targetUid: targetUserUid };
  }
  return { action: 'SIGN_IN_DIRECT', requiresMigration: false, targetUid: targetUserUid || currentUserUid };
}

function classifyAuthError(code) {
  switch (code) {
    case 'auth/credential-already-in-use':
    case 'auth/account-exists-with-different-credential':
      return { type: 'CONFLICT', shouldMigrate: true, userMessage: 'Existing account detected. Migrating guest cart...' };
    case 'auth/popup-closed-by-user':
    case 'auth/cancelled-popup-request':
      return { type: 'CANCELLED', shouldMigrate: false, userMessage: 'Sign-in popup closed before completion.' };
    case 'auth/popup-blocked':
      return { type: 'BLOCKED', shouldMigrate: false, userMessage: 'Popup blocked by browser. Please allow popups.' };
    case 'auth/unauthorized-domain':
      return { type: 'CONFIG_ERROR', shouldMigrate: false, userMessage: 'Domain not authorized in Firebase Console.' };
    case 'auth/operation-not-allowed':
      return { type: 'CONFIG_ERROR', shouldMigrate: false, userMessage: 'Authentication provider is disabled.' };
    case 'auth/user-not-found':
    case 'auth/invalid-credential':
    case 'auth/invalid-login-credentials':
      return { type: 'AUTO_CREATE_ELIGIBLE', shouldMigrate: false, userMessage: 'User does not exist yet. Initializing new account...' };
    case 'auth/weak-password':
      return { type: 'VALIDATION_ERROR', shouldMigrate: false, userMessage: 'Password must be at least 6 characters.' };
    default:
      return { type: 'UNKNOWN_ERROR', shouldMigrate: false, userMessage: 'Authentication failed.' };
  }
}

// ==============================================================================
// TEST SUITE DEFINITIONS
// ==============================================================================

describe('1. Firestore Security Rules (Unit Tests)', () => {
  it('allows owner to add valid quantity to cart', () => {
    const res = evaluateCartWrite('usr_alice', 'usr_alice', { qty: 2 });
    assert.equal(res.allowed, true);
  });

  it('rejects price tampering payload { qty: 1, price: 0.01 }', () => {
    const res = evaluateCartWrite('usr_alice', 'usr_alice', { qty: 1, price: 0.01 });
    assert.equal(res.allowed, false);
    assert.match(res.error, /keys must only contain qty/i);
  });

  it('rejects custom discount or promo fields', () => {
    const res = evaluateCartWrite('usr_alice', 'usr_alice', { qty: 1, discount: 0.9 });
    assert.equal(res.allowed, false);
  });

  it('rejects cross-user cart writes (User A writing to User B)', () => {
    const res = evaluateCartWrite('usr_alice', 'usr_bob', { qty: 1 });
    assert.equal(res.allowed, false);
    assert.match(res.error, /path uid mismatch/i);
  });

  it('rejects unauthenticated cart writes', () => {
    const res = evaluateCartWrite(null, 'usr_alice', { qty: 1 });
    assert.equal(res.allowed, false);
    assert.match(res.error, /unauthenticated/i);
  });

  it('rejects negative and zero quantities', () => {
    assert.equal(evaluateCartWrite('usr_alice', 'usr_alice', { qty: 0 }).allowed, false);
    assert.equal(evaluateCartWrite('usr_alice', 'usr_alice', { qty: -5 }).allowed, false);
  });

  it('rejects quantities exceeding 99 (overflow guard)', () => {
    assert.equal(evaluateCartWrite('usr_alice', 'usr_alice', { qty: 100 }).allowed, false);
    assert.equal(evaluateCartWrite('usr_alice', 'usr_alice', { qty: 99999 }).allowed, false);
  });

  it('rejects non-integer quantities (floats, strings, booleans)', () => {
    assert.equal(evaluateCartWrite('usr_alice', 'usr_alice', { qty: 2.5 }).allowed, false);
    assert.equal(evaluateCartWrite('usr_alice', 'usr_alice', { qty: '3' }).allowed, false);
    assert.equal(evaluateCartWrite('usr_alice', 'usr_alice', { qty: true }).allowed, false);
  });

  it('allows owner to delete item from cart', () => {
    const res = evaluateCartDelete('usr_alice', 'usr_alice');
    assert.equal(res.allowed, true);
  });

  it('blocks cross-user cart deletions', () => {
    const res = evaluateCartDelete('usr_alice', 'usr_bob');
    assert.equal(res.allowed, false);
  });

  it('allows public read of product catalog', () => {
    assert.equal(evaluateProductAccess('read').allowed, true);
  });

  it('blocks client writes to product catalog', () => {
    assert.equal(evaluateProductAccess('write', false).allowed, false);
  });

  it('rejects unsupported product catalog operations', () => {
    assert.equal(evaluateProductAccess('delete', false).allowed, false);
  });

  it('allows admin SDK writes to product catalog', () => {
    assert.equal(evaluateProductAccess('write', true).allowed, true);
  });

  it('blocks unscoped orders collection queries (rules are not filters)', () => {
    const res = evaluateOrdersRead('usr_alice', null, 'usr_alice');
    assert.equal(res.allowed, false);
    assert.match(res.error, /unscoped/i);
  });

  it('allows scoped orders query when where("ownerUid", "==", auth.uid) matches', () => {
    const res = evaluateOrdersRead('usr_alice', 'usr_alice', 'usr_alice');
    assert.equal(res.allowed, true);
  });

  it('blocks cross-user order document read', () => {
    const res = evaluateOrdersRead('usr_alice', 'usr_alice', 'usr_bob');
    assert.equal(res.allowed, false);
  });

  it('blocks client-side direct order creation', () => {
    assert.equal(evaluateOrdersWrite(false).allowed, false);
  });

  it('allows server admin order creation', () => {
    assert.equal(evaluateOrdersWrite(true).allowed, true);
  });
});

describe('2. Server Checkout Pricing Authority & Sanitization', () => {
  it('overrides forged client prices with canonical catalog pricing', () => {
    const tamperedCart = {
      prod_honey: { qty: 2, price: 0.01 }, // Canonical: $14.50 -> Expected $29.00
      prod_olive_oil: { qty: 1, price: 1.0 }, // Canonical: $18.00 -> Expected $18.00
    };
    const res = calculateServerOrder('usr_alice', tamperedCart);
    assert.equal(res.status, 200);
    assert.equal(res.order.total, 47.0);
    assert.equal(res.order.lines.find((l) => l.productId === 'prod_honey').unitPrice, 14.5);
  });

  it('handles direct scalar quantity format { prod_honey: 3 }', () => {
    const res = calculateServerOrder('usr_alice', { prod_honey: 3 });
    assert.equal(res.status, 200);
    assert.equal(res.order.total, 43.5);
  });

  it('clamps invalid quantities between 1 and 99', () => {
    const cart = {
      prod_honey: { qty: 999 }, // Clamps to 99 -> $1435.50
      prod_bread: { qty: -5 }, // Clamps to 1 -> $9.25
      prod_figs: { qty: 'invalid' }, // Fallback to 1 -> $8.00
    };
    const res = calculateServerOrder('usr_alice', cart);
    assert.equal(res.status, 200);
    assert.equal(res.order.lines.find((l) => l.productId === 'prod_honey').qty, 99);
    assert.equal(res.order.lines.find((l) => l.productId === 'prod_bread').qty, 1);
    assert.equal(res.order.lines.find((l) => l.productId === 'prod_figs').qty, 1);
  });

  it('rejects checkout with empty cart (400 Bad Request)', () => {
    const res = calculateServerOrder('usr_alice', {});
    assert.equal(res.status, 400);
    assert.match(res.error, /empty/i);
  });

  it('skips nonexistent product IDs safely', () => {
    const cart = {
      prod_fake_item: { qty: 10 },
      prod_coffee: { qty: 2 }, // $16.50 * 2 = $33.00
    };
    const res = calculateServerOrder('usr_alice', cart);
    assert.equal(res.status, 200);
    assert.equal(res.order.total, 33.0);
    assert.equal(res.order.lines.length, 1);
  });
});

describe('3. Guest Cart Migration & Authentication Resolution', () => {
  it('transfers disjoint items from guest cart to user cart', () => {
    const guestCart = { prod_honey: { qty: 2 } };
    const userCart = { prod_bread: { qty: 1 } };
    const merged = migrateGuestCart('anon_123', 'usr_alice', guestCart, userCart);

    assert.equal(merged.prod_honey.qty, 2);
    assert.equal(merged.prod_bread.qty, 1);
  });

  it('sums overlapping item quantities between guest and returning user', () => {
    const guestCart = { prod_figs: { qty: 3 }, prod_coffee: { qty: 1 } };
    const userCart = { prod_figs: { qty: 2 }, prod_cheese: { qty: 1 } };
    const merged = migrateGuestCart('anon_123', 'usr_alice', guestCart, userCart);

    assert.equal(merged.prod_figs.qty, 5); // 3 + 2
    assert.equal(merged.prod_coffee.qty, 1);
    assert.equal(merged.prod_cheese.qty, 1);
  });

  it('clamps merged item quantities at 99', () => {
    const guestCart = { prod_honey: { qty: 60 } };
    const userCart = { prod_honey: { qty: 50 } };
    const merged = migrateGuestCart('anon_123', 'usr_alice', guestCart, userCart);

    assert.equal(merged.prod_honey.qty, 99); // Clamped at 99
  });

  it('handles empty guest cart without altering user cart', () => {
    const userCart = { prod_bread: { qty: 2 } };
    const merged = migrateGuestCart('anon_123', 'usr_alice', {}, userCart);
    assert.deepEqual(merged, userCart);
  });

  it('preserves cart as no-op when user UID matches (linkWithPopup in-place)', () => {
    const originalCart = { prod_honey: { qty: 3 } };
    const merged = migrateGuestCart('usr_shared_123', 'usr_shared_123', originalCart, originalCart);
    assert.deepEqual(merged, originalCart);
  });

  it('handles mixed scalar quantities and object formats in guest cart', () => {
    const guestCart = { prod_honey: 4, prod_bread: { qty: 2 } };
    const userCart = { prod_honey: { qty: 1 } };
    const merged = migrateGuestCart('anon_123', 'usr_alice', guestCart, userCart);
    assert.equal(merged.prod_honey.qty, 5);
    assert.equal(merged.prod_bread.qty, 2);
  });

  it('resolves Google OAuth auth action matrix (link in-place vs migrate vs direct)', () => {
    // 1. Anonymous visitor linking Google account without prior account
    const linkRes = resolveGoogleAuthAction(true, 'anon_123', null);
    assert.equal(linkRes.action, 'LINK_IN_PLACE');
    assert.equal(linkRes.requiresMigration, false);

    // 2. Anonymous visitor linking Google account that already belongs to existing user
    const conflictRes = resolveGoogleAuthAction(true, 'anon_123', 'usr_returning_google');
    assert.equal(conflictRes.action, 'MIGRATE_AND_SWITCH');
    assert.equal(conflictRes.requiresMigration, true);
    assert.equal(conflictRes.targetUid, 'usr_returning_google');

    // 3. Non-anonymous user signing in directly
    const directRes = resolveGoogleAuthAction(false, 'usr_alice', 'usr_alice');
    assert.equal(directRes.action, 'SIGN_IN_DIRECT');
    assert.equal(directRes.requiresMigration, false);
  });

  it('classifies Firebase Auth error codes with actionable guidance', () => {
    // Credential conflict -> trigger migration
    assert.equal(classifyAuthError('auth/credential-already-in-use').shouldMigrate, true);
    assert.equal(classifyAuthError('auth/account-exists-with-different-credential').shouldMigrate, true);

    // Popup closed/cancelled -> non-intrusive info
    assert.equal(classifyAuthError('auth/popup-closed-by-user').type, 'CANCELLED');
    assert.equal(classifyAuthError('auth/cancelled-popup-request').type, 'CANCELLED');

    // Popup blocked
    assert.equal(classifyAuthError('auth/popup-blocked').type, 'BLOCKED');

    // Configuration requirements
    assert.equal(classifyAuthError('auth/unauthorized-domain').type, 'CONFIG_ERROR');
    assert.equal(classifyAuthError('auth/operation-not-allowed').type, 'CONFIG_ERROR');

    // Auto-create eligible demo errors
    assert.equal(classifyAuthError('auth/user-not-found').type, 'AUTO_CREATE_ELIGIBLE');
    assert.equal(classifyAuthError('auth/invalid-login-credentials').type, 'AUTO_CREATE_ELIGIBLE');

    // Weak password
    assert.equal(classifyAuthError('auth/weak-password').type, 'VALIDATION_ERROR');

    // Unknown errors fallback
    assert.equal(classifyAuthError('auth/internal-error').type, 'UNKNOWN_ERROR');
  });
});

describe('4. Live Cloud Run REST API Integration', () => {
  let liveAvailable = false;

  before(async () => {
    try {
      const res = await fetch(`${APP_URL}/api/config`);
      liveAvailable = res.status === 200;
    } catch {
      liveAvailable = false;
    }
  });

  it('GET /api/config returns GCP project metadata', async (t) => {
    if (!liveAvailable)
      return t.skip(`Endpoint unavailable at ${APP_URL} (set APP_URL=https://... to test)`);
    const res = await fetch(`${APP_URL}/api/config`);
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(data.projectId, 'projectId should be defined');
    assert.equal(data.authDomain, `${data.projectId}.firebaseapp.com`);
    assert.equal(data.storageBucket, `${data.projectId}.appspot.com`);
  });

  it('GET /api/products returns 8 canonical items', async (t) => {
    if (!liveAvailable) return t.skip(`Endpoint unavailable at ${APP_URL}`);
    const res = await fetch(`${APP_URL}/api/products`);
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.equal(data.products.length, 8);
  });

  it('POST /api/checkout rejects empty cart with 400', async (t) => {
    if (!liveAvailable) return t.skip(`Endpoint unavailable at ${APP_URL}`);
    const res = await fetch(`${APP_URL}/api/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid: 'node_test_user', items: {} }),
    });
    assert.equal(res.status, 400);
  });

  it('POST /api/checkout verifies catalog total and overrides forged price', async (t) => {
    if (!liveAvailable) return t.skip(`Endpoint unavailable at ${APP_URL}`);
    const res = await fetch(`${APP_URL}/api/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        uid: 'node_test_runner',
        items: {
          prod_bread: { qty: 1, price: 0.01 }, // $9.25
          prod_honey: { qty: 1 }, // $14.50
        },
      }),
    });
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.equal(data.success, true);
    assert.equal(data.order.total, 23.75);
    assert.equal(data.order.status, 'PAID_VERIFIED');
  });
});
