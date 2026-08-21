# Secure Shopping Cart with Firebase & Cloud Run

[![Cloud Run](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-4285F4?logo=googlecloud&logoColor=white)](https://cloud.google.com/run)
[![Cloud Firestore](https://img.shields.io/badge/Firebase-Cloud%20Firestore-FFCA28?logo=firebase&logoColor=black)](https://firebase.google.com/docs/firestore)
[![Firebase Auth](https://img.shields.io/badge/Firebase-Authentication-FFCA28?logo=firebase&logoColor=black)](https://firebase.google.com/docs/auth)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

An interactive, production-ready demonstration of **zero-trust serverless e-commerce architecture** on Google Cloud and Firebase.

This demo demonstrates how to combine **Firebase Anonymous Authentication**, **Path-Based Cloud Firestore Security Rules**, **Guest-to-Account Cart Migration**, and a **Server-Authoritative Cloud Run Backend** to deliver a fast, reactive frontend that is mathematically immune to client-side price tampering or unauthorized data access.

---

## 🏗️ Architecture Overview

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                            Browser Client                               │
 │                                                                         │
 │  ┌─────────────────────────┐            ┌────────────────────────────┐  │
 │  │ Firebase Auth Session   │            │ Live onSnapshot() Listener │  │
 │  │ (Anonymous / Permanent) │            │ /carts/{uid}/items         │  │
 │  └────────────┬────────────┘            └─────────────▲──────────────┘  │
 └───────────────┼───────────────────────────────────────┼─────────────────┘
                 │ 1. Mint Token / Link Account          │ 2. Real-time Cart Sync
                 ▼                                       │ (Owner-only path check)
 ┌───────────────────────────────┐         ┌─────────────┴─────────────────┐
 │    Firebase Authentication    │         │        Cloud Firestore        │
 │                               │         │                               │
 │ • signInAnonymously()         │         │ • /products/{id} (Public Read)│
 │ • linkWithCredential()        │         │ • /carts/{uid}/items/{id}     │
 │ • signInWithEmailAndPassword()│         │ • /orders/{orderId}           │
 └───────────────────────────────┘         └─────────────▲─────────────────┘
                                                         │ 4. Write Order & Wipe Cart
                 3. POST /api/checkout                   │    (IAM Admin Privileges)
                 (Product IDs & Quantities Only)         │
 ┌───────────────────────────────────────────────────────┴─────────────────┐
 │                        Cloud Run Backend Server                         │
 │                                                                         │
 │ • Node.js 24 API Container                                              │
 │ • Canonical Catalog Price Verification (Overrides forged client prices) │
 │ • Admin Order Creation via Google Cloud IAM Compute Service Account     │
 └─────────────────────────────────────────────────────────────────────────┘
```

### Separation of Responsibilities

| System Layer | Primary Responsibility | Key Security Guarantee |
| :--- | :--- | :--- |
| **Browser Client** | Real-time UI rendering and session continuity | Uses genuine Firebase Auth tokens; never calculates final charges |
| **Firestore Security Rules** | Data ownership and schema verification | Enforces `/carts/{uid}` path isolation and `.hasOnly(['qty'])` field rules |
| **Cloud Run Backend** | Price authority and immutable order writes | Queries canonical server catalog and writes orders via IAM privileges |

---

## ✨ Key Features & Security Patterns

### 1. Zero-Friction Anonymous Onboarding
* On initial page load, `signInAnonymously()` provisions a genuine Google cryptographic UID (`request.auth.uid`) without signup modals or passwords.
* The guest gets immediate, persistent cart synchronization across tabs without relying on fragile `localStorage` state.

### 2. Path-Based Firestore Rules with Strict Schema Enforcement
Cart items are stored under `/carts/{uid}/items/{productId}` and protected by declarative database rules:

```javascript
match /carts/{uid}/items/{id} {
  // 1. Path-based authorization: User A cannot read or write User B's cart
  // 2. Strict schema lockdown: Client can ONLY provide 'qty' (no price/discount injection)
  // 3. Range constraint: Integer between 1 and 99
  allow create, update: if request.auth != null 
                         && request.auth.uid == uid
                         && request.resource.data.keys().hasOnly(['qty'])
                         && request.resource.data.qty is int
                         && request.resource.data.qty > 0
                         && request.resource.data.qty <= 99;

  allow read, delete: if request.auth != null && request.auth.uid == uid;
}
```

### 3. Four-Step Guest-to-Account Cart Migration
When a guest decides to log into an existing account (such as `alice@example.com`), the application reconciles guest items with her permanent account:
1. **Snapshot:** Read temporary guest items from memory.
2. **Cleanup:** Delete guest cart documents in Firestore before auth state switch.
3. **Authenticate:** Sign into permanent returning account.
4. **Reconcile:** Batch merge guest items into the permanent user cart, summing duplicate quantities with a 99-item safety cap.

### 4. Server-Authoritative Price & Checkout Verification
* Clients **never** calculate order totals or write order documents (`match /orders/{id} { allow write: if false; }`).
* Checkout requests (`POST /api/checkout`) only submit product IDs and quantities.
* The Cloud Run server calculates the verified total using the canonical product catalog and writes the confirmed receipt using IAM Service Account credentials.

---

## 🚀 Quickstart & Deployment

### Prerequisites
* [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed and authenticated (`gcloud auth login`).
* [Firebase CLI (`firebase`)](https://firebase.google.com/docs/cli) installed (`npm install -g firebase-tools` & `firebase login`).
* Node.js 20+ (for local development) and Python 3.13+ (for test suites).
* A Google Cloud project with Billing enabled.

---

### Step 1: Enable APIs & Configure Firebase Authentication

1. Set your project environment variable:
   ```bash
   export PROJECT_ID="<YOUR_PROJECT_ID>"
   gcloud config set project $PROJECT_ID
   ```

2. Enable the required Google Cloud APIs:
   ```bash
   gcloud services enable \
     firestore.googleapis.com \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     identitytoolkit.googleapis.com \
     --project $PROJECT_ID
   ```

3. In the [Firebase Console](https://console.firebase.google.com/):
   * Navigate to **Authentication > Sign-in method**.
   * Enable **Anonymous**, **Google**, and **Email/Password** sign-in providers.
   * Under **Firestore Database**, create a database in **Native Mode**.

---

### Step 2: Grant Cloud Run IAM Privileges for Firestore

The Cloud Run backend writes confirmed orders and cleans up checked-out carts using IAM Admin credentials. Grant the default Compute service account the **Cloud Datastore User** role:

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/datastore.user"
```

---

### Step 3: Deploy Firestore Security Rules

Deploy the path-based security rules using the Firebase CLI:

```bash
firebase deploy --only firestore:rules --project $PROJECT_ID
```

---

### Step 4: Deploy Backend to Cloud Run

Deploy the containerized application directly from the source directory:

```bash
gcloud run deploy secure-shopping-cart \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
  --project $PROJECT_ID
```

Once deployment finishes, open the output `Service URL` in your browser. The frontend will automatically retrieve project metadata from `/api/config` and initialize Firebase Auth & Firestore.

---

### Step 5: Authorize Cloud Run Domain for OAuth (Required for Google Sign-In)

Firebase Authentication enforces an origin whitelist to prevent cross-site token interception. When deploying the application to Cloud Run, authorize your deployment URL:

1. Open the [Firebase Console](https://console.firebase.google.com/).
2. Select your project and navigate to **Authentication > Settings > Authorized domains**.
3. Click **Add domain**.
4. Enter your Cloud Run hostname (e.g., `shop-simulator-487309083045.us-central1.run.app` or your custom domain).
5. Click **Add**.

> [!TIP]
> `localhost` is authorized by default for local testing. If you see the browser console warning `iframe.js:309 Info: The current domain is not authorized for OAuth operations` or receive `auth/unauthorized-domain` during Google sign-in, adding your domain to this list resolves the issue immediately.

---

### 💻 Running Locally (Optional)

#### Local Node.js Server
```bash
# Set your Google Cloud project ID
export PROJECT_ID="<YOUR_PROJECT_ID>"
export FIREBASE_API_KEY="<YOUR_WEB_API_KEY>"

# Start server on http://localhost:8080
npm start
```

#### Running with Firebase Local Emulator Suite
```bash
# Start server targeting local Firestore emulator
export FIRESTORE_EMULATOR_HOST="localhost:8080"
npm start
```

---

## 🧪 Interactive Security Test Suite & Audit Log

The demo includes a built-in interactive test suite to verify security rules live in your browser:

| Test Action | Validation Scenario | Expected Outcome | Security Rule Guarantee |
| :--- | :--- | :--- | :--- |
| **Price Tampering ($0.01)** | Sends `{ qty: 1, price: 0.01 }` to `/carts/{uid}/items` | **HTTP 403 Denied** | `request.resource.data.keys().hasOnly(['qty'])` |
| **Cross-User Cart Access** | Attempts to write to `/carts/user_b_992/items/...` | **HTTP 403 Denied** | `request.auth.uid == uid` |
| **Unscoped Query** | Executes `db.collection('orders').get()` without filters | **HTTP 403 Denied** | Rules are not filters; queries must use `where("ownerUid", "==", auth.uid)` |
| **Invalid Quantity** | Attempts to submit `{ qty: 99999 }` or `{ qty: -5 }` | **HTTP 403 Denied** | `qty is int && qty > 0 && qty <= 99` |

---

## 🔬 Automated Testing & Coverage

This repository includes standalone test suites in both **JavaScript (Node.js native test runner)** and **Python (pytest)** that validate security rules, server pricing calculations, cart migrations, and live API contracts.

### 1. Run with Node.js / JavaScript (Zero External Dependencies)

Runs the built-in `node:test` suite with line and branch coverage:

```bash
npm test
# Or directly: node --test --experimental-test-coverage tests/server.test.js
```

Sample output:
```text
▶ 1. Firestore Security Rules (Unit Tests)
  ✔ allows owner to add valid quantity to cart (5ms)
  ✔ rejects price tampering payload { qty: 1, price: 0.01 } (1ms)
  ✔ rejects cross-user cart writes (User A writing to User B) (1ms)
  ...
▶ 2. Server Checkout Pricing Authority & Sanitization
  ✔ overrides forged client prices with canonical catalog pricing (1ms)
  ...
▶ 3. Guest Cart Migration & Conflict Resolution
  ✔ transfers disjoint items from guest cart to user cart (1ms)
  ...
▶ 4. Live Cloud Run REST API Integration
  ✔ GET /api/config returns GCP project metadata (203ms)
  ✔ POST /api/checkout verifies catalog total and overrides forged price (292ms)

ℹ tests 36
ℹ pass 36
ℹ fail 0
ℹ duration_ms 1478
----------------------------------------------------------------
file            | line % | branch % | funcs % | uncovered lines
----------------------------------------------------------------
server.test.js  |  99.48 |    86.87 |  100.00 |
----------------------------------------------------------------
```

---

### 2. Run with Python & Pytest (Python >= 3.13)

Runs the 44-assertion Python test suite with `pytest` and `pytest-cov`:

```bash
# Install optional test dependencies
pip install -e ".[test]"

# Run with pytest (includes 100% coverage and duration metrics)
pytest

# Or run with standard Python unittest (zero dependencies required)
python3 tests/test_security_rules.py
```

Sample output:
```text
============================= test session starts ==============================
rootdir: /path/to/secure-shopping-cart, configfile: pyproject.toml
collected 44 items                                                             

tests/test_security_rules.py::TestFirestoreSecurityRules::test_01_valid_cart_write_owner PASSED [  2%]
...
tests/test_security_rules.py::TestLiveCloudRunApi::test_live_api_products PASSED [100%]

================================ tests coverage ================================
Name                           Stmts   Miss  Cover   Missing
------------------------------------------------------------
tests/test_security_rules.py     395      0   100%
------------------------------------------------------------
TOTAL                            395      0   100%
============================== 44 passed in 0.71s ==============================
```

---

## 📂 Repository Structure

```text
.
├── Dockerfile                  # Container definition for Cloud Run
├── LICENSE                     # Apache 2.0 License
├── README.md                   # Project documentation
├── biome.json                  # Biome linter & formatter configuration
├── firebase.json               # Firebase configuration for rules deployment
├── firestore.rules             # Declarative security rules
├── package.json                # Node.js project manifest (zero npm dependencies)
├── pyproject.toml              # Python project metadata & test configuration
├── server.js                   # Cloud Run backend server (catalog authority)
├── public/                     # Frontend web client
│   └── index.html              # Reactive UI, live audit log, & verification suite
└── tests/                      # Automated test suites
    ├── server.test.js          # 36-test native Node.js test runner
    └── test_security_rules.py  # 44-test Python security verification suite
```

---

## 📄 License

Copyright 2026 Google LLC. Licensed under the Apache License, Version 2.0.
