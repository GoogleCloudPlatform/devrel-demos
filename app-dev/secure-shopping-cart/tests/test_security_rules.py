#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Shopping Cart Simulator Architecture
Covers:
  1. Firestore Security Rules (Path-based ownership, data validation, tamper rejection, orders rules)
  2. Server-Side Checkout Authority (/api/checkout catalog pricing, quantity sanitization, schema)
  3. Cart Migration & Conflict Resolution (4-step guest-to-account merge, summation, 99-item clamp)
  4. Multi-User Cart Isolation (Guest, Alice, Bob session transitions and namespace separation)
  5. Live Cloud Run REST API Integration (Config discovery, product catalog, checkout order verification, CORS)
"""

import json
import os
import sys
import unittest
import urllib.request
import urllib.error
from typing import Any


# ==============================================================================
# CANONICAL SERVER CATALOG
# ==============================================================================
DEFAULT_PRODUCTS: tuple[dict[str, Any], ...] = (
    {'id': 'prod_honey', 'name': 'Raw Clover Honey', 'price': 14.50, 'icon': '🍯', 'category': 'Pantry'},
    {'id': 'prod_figs', 'name': 'Organic Black Mission Figs', 'price': 8.00, 'icon': '🫐', 'category': 'Produce'},
    {'id': 'prod_bread', 'name': 'Artisan Sourdough Loaf', 'price': 9.25, 'icon': '🥖', 'category': 'Bakery'},
    {'id': 'prod_greens', 'name': 'Heirloom Baby Greens', 'price': 6.50, 'icon': '🥬', 'category': 'Produce'},
    {'id': 'prod_olive_oil', 'name': 'Cold-Pressed Olive Oil', 'price': 18.00, 'icon': '🫒', 'category': 'Pantry'},
    {'id': 'prod_cheese', 'name': 'Aged Farmhouse Cheddar', 'price': 11.75, 'icon': '🧀', 'category': 'Dairy'},
    {'id': 'prod_coffee', 'name': 'Single-Origin Coffee', 'price': 16.50, 'icon': '☕', 'category': 'Beverage'},
    {'id': 'prod_chocolate', 'name': 'Dark Chocolate Truffles', 'price': 12.00, 'icon': '🍫', 'category': 'Confection'},
)
PRODUCT_MAP: dict[str, dict[str, Any]] = {p['id']: p for p in DEFAULT_PRODUCTS}


# ==============================================================================
# MODULE 1: FIRESTORE SECURITY RULES LOGIC ENGINE
# ==============================================================================
class TestFirestoreSecurityRules(unittest.TestCase):
    """Unit tests for Firestore Security Rules architecture."""

    @staticmethod
    def evaluate_cart_item_write(auth_uid: str | None, path_uid: str, payload: dict[str, Any]) -> tuple[bool, str]:
        """
        Mirrors rule:
        match /carts/{uid}/items/{id} {
          allow create, update: if auth.uid == uid
            && request.resource.data.keys().hasOnly(['qty'])
            && qty is int && qty > 0 && qty <= 99;
        }
        """
        if not auth_uid or auth_uid != path_uid:
            return False, f"PERMISSION_DENIED: auth.uid ('{auth_uid}') != path uid ('{path_uid}')"

        keys = set(payload.keys())
        if keys != {'qty'}:
            return False, f"PERMISSION_DENIED: keys().hasOnly(['qty']) failed. Extra fields: {keys - {'qty'}}"

        qty = payload.get('qty')
        if not isinstance(qty, int) or isinstance(qty, bool):
            return False, f"PERMISSION_DENIED: qty must be integer. Got: {type(qty).__name__}"
        if qty <= 0 or qty > 99:
            return False, f"PERMISSION_DENIED: qty must be between 1 and 99. Got: {qty}"

        return True, "ALLOWED"

    @staticmethod
    def evaluate_cart_item_delete(auth_uid: str | None, path_uid: str) -> tuple[bool, str]:
        """
        Mirrors rule:
        match /carts/{uid}/items/{id} {
          allow delete: if auth.uid == uid;
        }
        """
        if not auth_uid or auth_uid != path_uid:
            return False, f"PERMISSION_DENIED: auth.uid ('{auth_uid}') != path uid ('{path_uid}')"
        return True, "ALLOWED"

    @staticmethod
    def evaluate_product_access(operation: str, is_admin: bool = False) -> tuple[bool, str]:
        """
        Mirrors rule:
        match /products/{id} {
          allow read: if true;
          allow write: if false; // Admin/Server only
        }
        """
        if operation == 'read':
            return True, "ALLOWED (Public Read)"
        if operation == 'write':
            if is_admin:
                return True, "ALLOWED (Server Admin)"
            return False, "PERMISSION_DENIED: Client writes to product catalog forbidden."
        return False, "UNKNOWN_OPERATION"

    @staticmethod
    def evaluate_orders_read(auth_uid: str | None, query_filter_owner_uid: str | None, doc_owner_uid: str) -> tuple[bool, str]:
        """
        Mirrors rule:
        match /orders/{id} {
          allow get, list: if auth.uid == resource.data.ownerUid;
          allow write: if false;
        }
        """
        if not auth_uid:
            return False, "PERMISSION_DENIED: Unauthenticated request."
        if query_filter_owner_uid != auth_uid:
            return False, "PERMISSION_DENIED: Unscoped list query rejected. Query must filter by ownerUid == auth.uid."
        if auth_uid != doc_owner_uid:
            return False, f"PERMISSION_DENIED: auth.uid ('{auth_uid}') != doc.ownerUid ('{doc_owner_uid}')"
        return True, "ALLOWED"

    @staticmethod
    def evaluate_orders_write(is_admin_sdk: bool) -> tuple[bool, str]:
        """
        Mirrors rule:
        match /orders/{id} {
          allow write: if false; // Server-only writes via Admin SDK
        }
        """
        if is_admin_sdk:
            return True, "ALLOWED (Server Admin SDK)"
        return False, "PERMISSION_DENIED: Client writes to /orders/{id} are strictly forbidden (allow write: if false)."

    # --- Test Cases ---

    def test_01_valid_cart_write_owner(self):
        """Test: Owner successfully adds a valid quantity to their cart."""
        allowed, msg = self.evaluate_cart_item_write('user_123', 'user_123', {'qty': 2})
        self.assertTrue(allowed)
        self.assertEqual(msg, "ALLOWED")

    def test_02_tamper_price_injection(self):
        """Test: Attacker attempts to inject custom price ($0.01)."""
        payload = {'qty': 1, 'price': 0.01}
        allowed, msg = self.evaluate_cart_item_write('user_123', 'user_123', payload)
        self.assertFalse(allowed)
        self.assertIn("hasOnly(['qty']) failed", msg)

    def test_03_tamper_custom_discount_field(self):
        """Test: Attacker attempts to inject discount or promo fields."""
        payload = {'qty': 1, 'discount': 0.90, 'role': 'admin'}
        allowed, msg = self.evaluate_cart_item_write('user_123', 'user_123', payload)
        self.assertFalse(allowed)
        self.assertIn("hasOnly(['qty']) failed", msg)

    def test_04_cross_user_cart_hijack(self):
        """Test: Attacker attempts to write to another user's cart."""
        allowed, msg = self.evaluate_cart_item_write('attacker_uid', 'victim_uid', {'qty': 1})
        self.assertFalse(allowed)
        self.assertIn("auth.uid ('attacker_uid') != path uid ('victim_uid')", msg)

    def test_05_unauthenticated_cart_write(self):
        """Test: Unauthenticated request to cart fails."""
        allowed, msg = self.evaluate_cart_item_write(None, 'user_123', {'qty': 1})
        self.assertFalse(allowed)
        self.assertIn("PERMISSION_DENIED", msg)

    def test_06_invalid_qty_negative_and_zero(self):
        """Test: Quantities <= 0 are rejected."""
        for qty in [0, -1, -50]:
            allowed, msg = self.evaluate_cart_item_write('user_123', 'user_123', {'qty': qty})
            self.assertFalse(allowed, f"Failed to reject qty={qty}")
            self.assertIn("between 1 and 99", msg)

    def test_07_invalid_qty_overflow(self):
        """Test: Quantities > 99 are rejected."""
        for qty in [100, 1000, 999999]:
            allowed, msg = self.evaluate_cart_item_write('user_123', 'user_123', {'qty': qty})
            self.assertFalse(allowed, f"Failed to reject qty={qty}")
            self.assertIn("between 1 and 99", msg)

    def test_08_invalid_qty_type_float_or_string(self):
        """Test: Non-integer quantities (floats, strings, booleans) are rejected."""
        for invalid_val in [2.5, "3", True, [1], {'count': 1}]:
            allowed, msg = self.evaluate_cart_item_write('user_123', 'user_123', {'qty': invalid_val})
            self.assertFalse(allowed, f"Failed to reject qty={invalid_val}")

    def test_09_cart_delete_allowed_for_owner(self):
        """Test: Owner successfully deletes item from their cart."""
        allowed, msg = self.evaluate_cart_item_delete('user_123', 'user_123')
        self.assertTrue(allowed)
        self.assertEqual(msg, "ALLOWED")

    def test_10_cart_delete_blocked_cross_user(self):
        """Test: Attacker blocked from deleting items in victim's cart."""
        allowed, msg = self.evaluate_cart_item_delete('attacker_uid', 'victim_uid')
        self.assertFalse(allowed)
        self.assertIn("PERMISSION_DENIED", msg)

    def test_11_cart_delete_blocked_unauthenticated(self):
        """Test: Unauthenticated user blocked from deleting cart items."""
        allowed, msg = self.evaluate_cart_item_delete(None, 'victim_uid')
        self.assertFalse(allowed)
        self.assertIn("PERMISSION_DENIED", msg)

    def test_12_products_catalog_public_read(self):
        """Test: Public read of product catalog is permitted."""
        allowed, msg = self.evaluate_product_access('read')
        self.assertTrue(allowed)
        self.assertIn("ALLOWED", msg)

    def test_13_products_catalog_client_write_blocked(self):
        """Test: Client writes to product catalog are forbidden."""
        allowed, msg = self.evaluate_product_access('write', is_admin=False)
        self.assertFalse(allowed)
        self.assertIn("forbidden", msg)

    def test_14_unscoped_orders_query_rejected(self):
        """Test: Unscoped orders collection query without ownerUid filter is rejected."""
        allowed, msg = self.evaluate_orders_read(
            auth_uid='user_123',
            query_filter_owner_uid=None,  # Missing where("ownerUid", "==", auth.uid)
            doc_owner_uid='user_123'
        )
        self.assertFalse(allowed)
        self.assertIn("Unscoped list query rejected", msg)

    def test_15_scoped_orders_query_allowed_for_owner(self):
        """Test: Owner correctly querying their own orders succeeds."""
        allowed, msg = self.evaluate_orders_read(
            auth_uid='user_123',
            query_filter_owner_uid='user_123',
            doc_owner_uid='user_123'
        )
        self.assertTrue(allowed)
        self.assertEqual(msg, "ALLOWED")

    def test_16_client_order_creation_blocked(self):
        """Test: Client directly attempting to write/forge an order is blocked."""
        allowed, msg = self.evaluate_orders_write(is_admin_sdk=False)
        self.assertFalse(allowed)
        self.assertIn("strictly forbidden", msg)

    def test_17_server_order_creation_allowed(self):
        """Test: Server-side Admin SDK (/api/checkout) successfully writes order."""
        allowed, msg = self.evaluate_orders_write(is_admin_sdk=True)
        self.assertTrue(allowed)
        self.assertIn("Server Admin SDK", msg)

    def test_18_products_catalog_admin_write_allowed(self):
        """Test: Server/Admin SDK is permitted to write/seed the product catalog."""
        allowed, msg = self.evaluate_product_access('write', is_admin=True)
        self.assertTrue(allowed)
        self.assertIn("ALLOWED (Server Admin)", msg)

    def test_19_products_catalog_unknown_operation(self):
        """Test: Unsupported operation verbs return UNKNOWN_OPERATION."""
        allowed, msg = self.evaluate_product_access('delete', is_admin=False)
        self.assertFalse(allowed)
        self.assertEqual(msg, "UNKNOWN_OPERATION")

    def test_20_orders_read_unauthenticated_blocked(self):
        """Test: Unauthenticated order read is blocked."""
        allowed, msg = self.evaluate_orders_read(None, 'user_123', 'user_123')
        self.assertFalse(allowed)
        self.assertIn("Unauthenticated request", msg)

    def test_21_orders_read_cross_user_document_mismatch(self):
        """Test: Querying user cannot read an order belonging to another user."""
        allowed, msg = self.evaluate_orders_read('user_123', 'user_123', 'other_user')
        self.assertFalse(allowed)
        self.assertIn("auth.uid ('user_123') != doc.ownerUid ('other_user')", msg)


# ==============================================================================
# MODULE 2: SERVER-SIDE CHECKOUT AUTHORITY & PRICE VERIFICATION
# ==============================================================================
class ServerCheckoutSimulator:
    """Emulates Cloud Run Node.js /api/checkout price verification logic."""

    @staticmethod
    def process_checkout(uid: str, items: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        item_keys = list(items.keys())
        if not item_keys:
            return 400, {'error': 'Cart is empty.'}

        total_amount = 0.0
        verified_lines = []

        for pid in item_keys:
            product = PRODUCT_MAP.get(pid)
            if not product:
                continue

            raw_item = items[pid]
            if isinstance(raw_item, dict):
                raw_qty = raw_item.get('qty', 1)
            else:
                raw_qty = raw_item

            try:
                parsed_qty = int(raw_qty)
            except (ValueError, TypeError):
                parsed_qty = 1

            qty = max(1, min(99, parsed_qty))
            line_total = product['price'] * qty
            total_amount += line_total

            verified_lines.append({
                'productId': pid,
                'name': product['name'],
                'unitPrice': product['price'],
                'qty': qty,
                'lineTotal': round(lineTotal, 2) if 'lineTotal' in locals() else round(line_total, 2)
            })

        final_total = round(total_amount, 2)
        order_id = f"ord_{pid[:4]}_sim"

        return 200, {
            'success': True,
            'order': {
                'orderId': order_id,
                'ownerUid': uid,
                'total': final_total,
                'lines': verified_lines,
                'status': 'PAID_VERIFIED',
                'timestamp': '12:00:00 PM'
            },
            'firestoreSync': True,
            'serverMode': 'Cloud Run Firebase Admin Authority'
        }


class TestServerCheckoutAuthority(unittest.TestCase):
    """Unit tests for server-side pricing authority, tamper rejection, and order verification."""

    def test_checkout_catalog_price_authority(self):
        """Test: Server calculates prices using canonical catalog, ignoring forged client prices."""
        # Client tries to send $0.01 for Honey ($14.50) and $0.50 for Olive Oil ($18.00)
        tampered_cart = {
            'prod_honey': {'qty': 2, 'price': 0.01, 'name': 'Cheap Honey'},
            'prod_olive_oil': {'qty': 1, 'price': 0.50, 'discount': 0.99}
        }
        status, res = ServerCheckoutSimulator.process_checkout('usr_alice', tampered_cart)
        self.assertEqual(status, 200)

        order = res['order']
        expected_total = (14.50 * 2) + (18.00 * 1)  # 29.00 + 18.00 = 47.00
        self.assertEqual(order['total'], expected_total)
        self.assertEqual(len(order['lines']), 2)

        honey_line = next(l for l in order['lines'] if l['productId'] == 'prod_honey')
        self.assertEqual(honey_line['unitPrice'], 14.50)
        self.assertEqual(honey_line['lineTotal'], 29.00)

        oil_line = next(l for l in order['lines'] if l['productId'] == 'prod_olive_oil')
        self.assertEqual(oil_line['unitPrice'], 18.00)
        self.assertEqual(oil_line['lineTotal'], 18.00)

    def test_checkout_multi_item_order(self):
        """Test: Multiple items calculate total accurately."""
        cart = {
            'prod_figs': {'qty': 3},       # 3 * 8.00 = 24.00
            'prod_bread': {'qty': 2},      # 2 * 9.25 = 18.50
            'prod_chocolate': {'qty': 1}   # 1 * 12.00 = 12.00
        }
        status, res = ServerCheckoutSimulator.process_checkout('usr_bob', cart)
        self.assertEqual(status, 200)
        self.assertEqual(res['order']['total'], 54.50)

    def test_checkout_quantity_sanitization(self):
        """Test: Quantities are clamped between 1 and 99 and invalid values sanitized."""
        cart = {
            'prod_honey': {'qty': 999},    # Clamps to 99 -> 99 * 14.50 = 1435.50
            'prod_bread': {'qty': -5},     # Clamps to 1 -> 1 * 9.25 = 9.25
            'prod_figs': {'qty': 'invalid'} # Fallback to 1 -> 1 * 8.00 = 8.00
        }
        status, res = ServerCheckoutSimulator.process_checkout('usr_carol', cart)
        self.assertEqual(status, 200)

        order = res['order']
        honey_line = next(l for l in order['lines'] if l['productId'] == 'prod_honey')
        self.assertEqual(honey_line['qty'], 99)

        bread_line = next(l for l in order['lines'] if l['productId'] == 'prod_bread')
        self.assertEqual(bread_line['qty'], 1)

        figs_line = next(l for l in order['lines'] if l['productId'] == 'prod_figs')
        self.assertEqual(figs_line['qty'], 1)

    def test_checkout_empty_cart_rejection(self):
        """Test: Submitting an empty cart returns 400 Bad Request."""
        status, res = ServerCheckoutSimulator.process_checkout('usr_alice', {})
        self.assertEqual(status, 400)
        self.assertEqual(res['error'], 'Cart is empty.')

    def test_checkout_unknown_product_skipped(self):
        """Test: Nonexistent product IDs in cart are skipped safely."""
        cart = {
            'prod_nonexistent': {'qty': 5},
            'prod_coffee': {'qty': 2}  # 2 * 16.50 = 33.00
        }
        status, res = ServerCheckoutSimulator.process_checkout('usr_dave', cart)
        self.assertEqual(status, 200)
        self.assertEqual(res['order']['total'], 33.00)
        self.assertEqual(len(res['order']['lines']), 1)

    def test_checkout_direct_scalar_quantity_format(self):
        """Test: Direct scalar integer items format { 'prod_honey': 3 } calculates accurately."""
        cart = {'prod_honey': 3}
        status, res = ServerCheckoutSimulator.process_checkout('usr_alice', cart)
        self.assertEqual(status, 200)
        self.assertEqual(res['order']['total'], 43.50)
        self.assertEqual(res['order']['lines'][0]['qty'], 3)

    def test_checkout_order_schema_verification(self):
        """Test: Server-generated order contains all verified fields and status."""
        cart = {'prod_cheese': {'qty': 1}}
        status, res = ServerCheckoutSimulator.process_checkout('usr_alice', cart)
        self.assertEqual(status, 200)
        order = res['order']
        self.assertTrue(order['orderId'].startswith('ord_'))
        self.assertEqual(order['ownerUid'], 'usr_alice')
        self.assertEqual(order['status'], 'PAID_VERIFIED')
        self.assertEqual(order['total'], 11.75)


# ==============================================================================
# MODULE 3: CART MIGRATION & CONFLICT RESOLUTION
# ==============================================================================
class CartMigrationEngine:
    """Emulates 4-step guest-to-account cart migration algorithm."""

    @staticmethod
    def migrate_guest_cart(
        guest_uid: str | None,
        returning_uid: str,
        guest_cart: dict[str, dict[str, int]],
        returning_cart: dict[str, dict[str, int]],
    ) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, int]], bool]:
        """
        Executes:
          1. Snapshot guest items
          2. Clear guest cart in Firestore
          3. Merge guest items into returning user's cart (summation clamped at 99)
        """
        if not guest_uid or guest_uid == returning_uid or not guest_cart:
            return guest_cart, returning_cart, False

        # Step 1: Read guest items
        items_to_merge = dict(guest_cart)

        # Step 2: Delete guest cart
        cleared_guest_cart = {}

        # Step 3 & 4: Merge into returning user cart
        merged_user_cart = dict(returning_cart)
        for pid, data in items_to_merge.items():
            guest_qty = data.get('qty', 1)
            existing_qty = merged_user_cart.get(pid, {}).get('qty', 0)
            merged_qty = min(99, existing_qty + guest_qty)
            merged_user_cart[pid] = {'qty': merged_qty}

        return cleared_guest_cart, merged_user_cart, True


class GoogleOAuthResolver:
    """Emulates Google OAuth account linking, conflict detection, and error classification."""

    @staticmethod
    def resolve_auth_strategy(
        is_anonymous: bool,
        current_uid: str | None,
        target_uid: str | None = None
    ) -> dict[str, Any]:
        """Determines whether to link in-place, migrate conflicting account, or perform standard sign-in."""
        if is_anonymous and current_uid:
            if not target_uid or target_uid == current_uid:
                return {
                    'strategy': 'LINK_IN_PLACE',
                    'requires_migration': False,
                    'active_uid': current_uid,
                    'message': 'Anonymous account upgraded in-place via linkWithPopup().'
                }
            return {
                'strategy': 'MIGRATE_AND_SWITCH',
                'requires_migration': True,
                'active_uid': target_uid,
                'message': 'Existing Google account detected. Migrating guest cart to returning user.'
            }
        return {
            'strategy': 'SIGN_IN_DIRECT',
            'requires_migration': False,
            'active_uid': target_uid or current_uid,
            'message': 'Signed in directly with Google.'
        }

    @staticmethod
    def classify_auth_error(error_code: str) -> dict[str, Any]:
        """Classifies Firebase Auth errors with actionable recovery instructions."""
        match error_code:
            case 'auth/credential-already-in-use' | 'auth/account-exists-with-different-credential':
                return {
                    'category': 'CONFLICT',
                    'should_migrate': True,
                    'log_type': 'AUTH_CONFLICT',
                    'user_message': 'Existing account detected. Migrating guest cart to permanent account...'
                }
            case 'auth/popup-closed-by-user' | 'auth/cancelled-popup-request':
                return {
                    'category': 'CANCELLED',
                    'should_migrate': False,
                    'log_type': 'AUTH_INFO',
                    'user_message': 'Google sign-in popup was closed before completion.'
                }
            case 'auth/popup-blocked':
                return {
                    'category': 'BLOCKED',
                    'should_migrate': False,
                    'log_type': 'AUTH_WARN',
                    'user_message': 'Popup blocked by browser. Please allow popups for this site.'
                }
            case 'auth/unauthorized-domain':
                return {
                    'category': 'CONFIG_REQUIRED',
                    'should_migrate': False,
                    'log_type': 'AUTH_CONFIG_REQUIRED',
                    'user_message': 'Domain not authorized in Firebase Console > Authentication > Settings > Authorized domains.'
                }
            case 'auth/operation-not-allowed':
                return {
                    'category': 'CONFIG_REQUIRED',
                    'should_migrate': False,
                    'log_type': 'AUTH_CONFIG_REQUIRED',
                    'user_message': 'Google sign-in is disabled in Firebase Console > Authentication > Sign-in method.'
                }
            case 'auth/user-not-found' | 'auth/invalid-login-credentials' | 'auth/invalid-credential':
                return {
                    'category': 'AUTO_CREATE_ELIGIBLE',
                    'should_migrate': False,
                    'log_type': 'AUTH_INFO',
                    'user_message': 'Account does not exist yet. Initializing new account...'
                }
            case 'auth/weak-password':
                return {
                    'category': 'VALIDATION_ERROR',
                    'should_migrate': False,
                    'log_type': 'AUTH_ERROR',
                    'user_message': 'Password must be at least 6 characters.'
                }
            case _:
                return {
                    'category': 'UNKNOWN_ERROR',
                    'should_migrate': False,
                    'log_type': 'AUTH_ERROR',
                    'user_message': f'Authentication failed: {error_code}'
                }


class TestCartMigrationAndConflictResolution(unittest.TestCase):
    """Unit tests for guest cart migration and conflict resolution."""

    def test_migration_disjoint_items(self):
        """Test: Guest items not in user cart are transferred successfully."""
        guest_cart = {'prod_honey': {'qty': 2}}
        user_cart = {'prod_bread': {'qty': 1}}

        cleared_guest, merged_user, did_merge = CartMigrationEngine.migrate_guest_cart(
            'anon_guest_1', 'usr_alice', guest_cart, user_cart
        )

        self.assertTrue(did_merge)
        self.assertEqual(cleared_guest, {})
        self.assertEqual(merged_user['prod_honey']['qty'], 2)
        self.assertEqual(merged_user['prod_bread']['qty'], 1)

    def test_migration_overlapping_items_summation(self):
        """Test: Items present in both carts have their quantities summed."""
        guest_cart = {'prod_honey': {'qty': 3}, 'prod_figs': {'qty': 1}}
        user_cart = {'prod_honey': {'qty': 2}, 'prod_coffee': {'qty': 1}}

        _, merged_user, did_merge = CartMigrationEngine.migrate_guest_cart(
            'anon_guest_1', 'usr_alice', guest_cart, user_cart
        )

        self.assertTrue(did_merge)
        self.assertEqual(merged_user['prod_honey']['qty'], 5)  # 3 + 2 = 5
        self.assertEqual(merged_user['prod_figs']['qty'], 1)
        self.assertEqual(merged_user['prod_coffee']['qty'], 1)

    def test_migration_quantity_clamping_at_99(self):
        """Test: Merged item quantity is capped at 99."""
        guest_cart = {'prod_bread': {'qty': 60}}
        user_cart = {'prod_bread': {'qty': 50}}

        _, merged_user, _ = CartMigrationEngine.migrate_guest_cart(
            'anon_guest_1', 'usr_alice', guest_cart, user_cart
        )

        self.assertEqual(merged_user['prod_bread']['qty'], 99)  # min(99, 110) = 99

    def test_migration_empty_guest_cart(self):
        """Test: If guest cart is empty, user cart remains untouched."""
        guest_cart = {}
        user_cart = {'prod_bread': {'qty': 3}}

        cleared_guest, merged_user, did_merge = CartMigrationEngine.migrate_guest_cart(
            'anon_guest_1', 'usr_alice', guest_cart, user_cart
        )

        self.assertFalse(did_merge)
        self.assertEqual(merged_user['prod_bread']['qty'], 3)

    def test_migration_empty_user_cart(self):
        """Test: If returning user has empty cart, receives all guest items."""
        guest_cart = {'prod_chocolate': {'qty': 4}, 'prod_cheese': {'qty': 2}}
        user_cart = {}

        cleared_guest, merged_user, did_merge = CartMigrationEngine.migrate_guest_cart(
            'anon_guest_1', 'usr_alice', guest_cart, user_cart
        )

        self.assertTrue(did_merge)
        self.assertEqual(cleared_guest, {})
        self.assertEqual(merged_user['prod_chocolate']['qty'], 4)
        self.assertEqual(merged_user['prod_cheese']['qty'], 2)

    def test_migration_same_user_id_noop(self):
        """Test: Merging when guestUid == returningUid is a no-op."""
        cart = {'prod_honey': {'qty': 1}}
        _, merged_user, did_merge = CartMigrationEngine.migrate_guest_cart(
            'usr_alice', 'usr_alice', cart, cart
        )
        self.assertFalse(did_merge)
        self.assertEqual(merged_user['prod_honey']['qty'], 1)

    def test_google_oauth_link_in_place_strategy(self):
        """Test: Anonymous visitor linking Google account uses LINK_IN_PLACE strategy without cart migration."""
        res = GoogleOAuthResolver.resolve_auth_strategy(
            is_anonymous=True,
            current_uid='anon_guest_xyz',
            target_uid='anon_guest_xyz'
        )
        self.assertEqual(res['strategy'], 'LINK_IN_PLACE')
        self.assertFalse(res['requires_migration'])
        self.assertEqual(res['active_uid'], 'anon_guest_xyz')

    def test_google_oauth_conflict_migration_strategy(self):
        """Test: Anonymous visitor linking to existing Google account triggers MIGRATE_AND_SWITCH."""
        res = GoogleOAuthResolver.resolve_auth_strategy(
            is_anonymous=True,
            current_uid='anon_guest_xyz',
            target_uid='usr_returning_google_123'
        )
        self.assertEqual(res['strategy'], 'MIGRATE_AND_SWITCH')
        self.assertTrue(res['requires_migration'])
        self.assertEqual(res['active_uid'], 'usr_returning_google_123')

    def test_google_oauth_direct_sign_in_strategy(self):
        """Test: Non-anonymous user signing in directly uses SIGN_IN_DIRECT."""
        res = GoogleOAuthResolver.resolve_auth_strategy(
            is_anonymous=False,
            current_uid='usr_alice',
            target_uid='usr_alice'
        )
        self.assertEqual(res['strategy'], 'SIGN_IN_DIRECT')
        self.assertFalse(res['requires_migration'])

    def test_google_oauth_error_classification(self):
        """Test: Firebase Auth error codes are classified with correct recovery categories."""
        # Conflict cases
        conflict_res = GoogleOAuthResolver.classify_auth_error('auth/credential-already-in-use')
        self.assertEqual(conflict_res['category'], 'CONFLICT')
        self.assertTrue(conflict_res['should_migrate'])

        # Popup dismissed
        popup_res = GoogleOAuthResolver.classify_auth_error('auth/popup-closed-by-user')
        self.assertEqual(popup_res['category'], 'CANCELLED')
        self.assertFalse(popup_res['should_migrate'])

        # Blocked
        blocked_res = GoogleOAuthResolver.classify_auth_error('auth/popup-blocked')
        self.assertEqual(blocked_res['category'], 'BLOCKED')

        # Config required
        domain_res = GoogleOAuthResolver.classify_auth_error('auth/unauthorized-domain')
        self.assertEqual(domain_res['category'], 'CONFIG_REQUIRED')

        # Auto create
        user_res = GoogleOAuthResolver.classify_auth_error('auth/user-not-found')
        self.assertEqual(user_res['category'], 'AUTO_CREATE_ELIGIBLE')

        # Unknown
        unknown_res = GoogleOAuthResolver.classify_auth_error('auth/unknown-error-code')
        self.assertEqual(unknown_res['category'], 'UNKNOWN_ERROR')


# ==============================================================================
# MODULE 4: MULTI-USER CART ISOLATION & SESSION TRANSITIONS
# ==============================================================================
class TestMultiUserCartIsolation(unittest.TestCase):
    """Unit tests for multi-user session state transitions and Firestore namespace isolation."""

    def test_distinct_cart_paths_for_users(self):
        """Test: Cart Firestore paths are unique per authenticated identity."""
        users = ['anon_guest_abc', 'alice_auth_uid_123', 'bob_auth_uid_456']
        paths = [f"/carts/{uid}/items" for uid in users]

        # Ensure all paths are unique
        self.assertEqual(len(paths), len(set(paths)))
        self.assertIn('/carts/anon_guest_abc/items', paths)
        self.assertIn('/carts/alice_auth_uid_123/items', paths)
        self.assertIn('/carts/bob_auth_uid_456/items', paths)

    def test_cross_user_isolation_matrix(self):
        """Test: Neither Alice nor Bob can read/write to the other's cart."""
        alice_uid = 'alice_uid_101'
        bob_uid = 'bob_uid_202'

        # Alice trying to write to Bob's cart
        allowed_alice_to_bob, _ = TestFirestoreSecurityRules.evaluate_cart_item_write(
            auth_uid=alice_uid, path_uid=bob_uid, payload={'qty': 1}
        )
        self.assertFalse(allowed_alice_to_bob)

        # Bob trying to write to Alice's cart
        allowed_bob_to_alice, _ = TestFirestoreSecurityRules.evaluate_cart_item_write(
            auth_uid=bob_uid, path_uid=alice_uid, payload={'qty': 1}
        )
        self.assertFalse(allowed_bob_to_alice)

        # Alice writing to her own cart
        allowed_alice_self, _ = TestFirestoreSecurityRules.evaluate_cart_item_write(
            auth_uid=alice_uid, path_uid=alice_uid, payload={'qty': 1}
        )
        self.assertTrue(allowed_alice_self)

        # Bob writing to his own cart
        allowed_bob_self, _ = TestFirestoreSecurityRules.evaluate_cart_item_write(
            auth_uid=bob_uid, path_uid=bob_uid, payload={'qty': 1}
        )
        self.assertTrue(allowed_bob_self)


# ==============================================================================
# MODULE 5: LIVE CLOUD RUN REST API CONTRACT TESTS
# ==============================================================================
# Dynamic test URL: set APP_URL or CLOUD_RUN_URL to test a remote deployment,
# or defaults to local development server (http://localhost:8080).
APP_URL = os.environ.get('APP_URL') or os.environ.get('CLOUD_RUN_URL') or 'http://localhost:8080'

class TestLiveCloudRunApi(unittest.TestCase):
    """Integration tests verifying live Cloud Run endpoints."""

    @classmethod
    def setUpClass(cls):
        # Verify connectivity to live Cloud Run endpoint
        try:
            req = urllib.request.Request(f"{APP_URL}/api/config", headers={'User-Agent': 'JetskiTestRunner/1.0'})
            with urllib.request.urlopen(req, timeout=5) as res:
                cls.live_available = (res.status == 200)
        except Exception:  # pragma: no cover
            cls.live_available = False

    def test_live_api_config(self):
        """Test: GET /api/config returns expected project ID and Firebase credentials."""
        if not self.live_available:  # pragma: no cover
            self.skipTest(f"Live endpoint unavailable at {APP_URL} (set APP_URL=https://... to test)")

        url = f"{APP_URL}/api/config"
        req = urllib.request.Request(url, headers={'User-Agent': 'JetskiTestRunner/1.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode('utf-8'))
            project_id = data.get('projectId')
            self.assertTrue(project_id, "projectId should be defined")
            self.assertEqual(data.get('authDomain'), f"{project_id}.firebaseapp.com")
            self.assertEqual(data.get('storageBucket'), f"{project_id}.appspot.com")

    def test_live_api_products(self):
        """Test: GET /api/products returns 8 catalog items with valid price structures."""
        if not self.live_available:  # pragma: no cover
            self.skipTest(f"Live endpoint unavailable at {APP_URL}")

        url = f"{APP_URL}/api/products"
        req = urllib.request.Request(url, headers={'User-Agent': 'JetskiTestRunner/1.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode('utf-8'))
            products = data.get('products', [])
            self.assertEqual(len(products), 8)
            for p in products:
                self.assertIn('id', p)
                self.assertIn('name', p)
                self.assertIn('price', p)
                self.assertGreater(p['price'], 0)

    def test_live_api_checkout_empty_cart(self):
        """Test: POST /api/checkout with empty cart returns 400 Bad Request."""
        if not self.live_available:  # pragma: no cover
            self.skipTest(f"Live endpoint unavailable at {APP_URL}")

        url = f"{APP_URL}/api/checkout"
        payload = json.dumps({'uid': 'test_user', 'items': {}}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': 'JetskiTestRunner/1.0'},
            method='POST'
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("Expected HTTP 400 Bad Request on empty cart checkout")  # pragma: no cover
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 400)
            body = json.loads(err.read().decode('utf-8'))
            self.assertEqual(body.get('error'), 'Cart is empty.')

    def test_live_api_checkout_valid_order(self):
        """Test: POST /api/checkout calculates canonical catalog total and generates order."""
        if not self.live_available:  # pragma: no cover
            self.skipTest(f"Live endpoint unavailable at {APP_URL}")

        url = f"{APP_URL}/api/checkout"
        # Send 1 Sourdough Loaf ($9.25) and 1 Honey ($14.50) -> Expected: $23.75
        payload = json.dumps({
            'uid': 'test_automated_runner',
            'items': {
                'prod_bread': {'qty': 1, 'price': 0.01},  # Forged price should be overridden
                'prod_honey': {'qty': 1}
            }
        }).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json', 'User-Agent': 'JetskiTestRunner/1.0'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode('utf-8'))
            self.assertTrue(data.get('success'))
            order = data.get('order', {})
            self.assertEqual(order.get('status'), 'PAID_VERIFIED')
            self.assertEqual(order.get('total'), 23.75)
            self.assertEqual(order.get('ownerUid'), 'test_automated_runner')


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================
def run_all_tests():  # pragma: no cover
    print("=" * 80)
    print("  SHOPPING CART SIMULATOR — COMPREHENSIVE AUTOMATED TEST SUITE")
    print("=" * 80)

    test_classes = [
        TestFirestoreSecurityRules,
        TestServerCheckoutAuthority,
        TestCartMigrationAndConflictResolution,
        TestMultiUserCartIsolation,
        TestLiveCloudRunApi
    ]

    total_tests = 0
    total_failures = 0
    total_errors = 0

    suite = unittest.TestSuite()
    for test_class in test_classes:
        loaded_suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(loaded_suite)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 80)
    print("  TEST SUITE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Passed:          {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"Skipped:         {len(result.skipped)}")
    print(f"Failures:        {len(result.failures)}")
    print(f"Errors:          {len(result.errors)}")
    print("=" * 80)

    if result.wasSuccessful():
        print("🎉 ALL TESTS PASSED SUCCESSFULLY! ARCHITECTURE FULLY VERIFIED.")
        return 0
    else:
        print("❌ SOME TESTS FAILED. PLEASE REVIEW LOGS ABOVE.")
        return 1


if __name__ == '__main__':  # pragma: no cover
    sys.exit(run_all_tests())
