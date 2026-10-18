# ⚡ Flow: Autonomous B2B Idle Compute & Power Marketplace Simulation

> **Autonomous multi-agent matchmaker that simulates routing frontier AI lab workload bursts to enterprise off-peak idle power and compute on Google Cloud.**

Flow solves the dual challenge of the AI infrastructure crunch and grid saturation:
1. **Enterprises (Banks, Architecture Studios, Data Centers)** possess massive off-peak, clean power and reserved compute (Confidential VMs, L4/A100/H100 GPUs) that sits idle overnight.
2. **Frontier AI Labs** need low-cost, low-carbon burst capacity for model evaluation, synthetic data generation, and batch training.
3. **Flow's Autonomous Agent Platform Architecture** establishes provisional holds, coordinates a **2-Officer Sequential Multi-Model Zero-Trust Security Council** debate, commits signed leases, and records immutable cryptographic SHA-256 receipts on Cloud Run.

![Flow Marketplace Home](./assets/flow_home.png)

---

## 🖥️ Interactive Dashboard Preview

### Security Council Benchmark Stats (`Stats` Tab)
Compare multi-model and Big Five (OCEAN) persona Security Council configurations across 100-contract stratified runs, tracking threat **Sensitivity**, benign **Specificity**, and approval/block/escalation/leak outcomes:

![Flow Security Council Stats](./assets/flow_stats.png)

### Buyer Workload Proposals & Audit Ledger (`Proposals` Tab)
Inspect every evaluated proposal across simulation runs, filter by ledger state (`COMMITTED`, `REJECTED`, `ESCALATED`), and drill into full 2-Officer sequential transcripts and SHA-256 receipts:

![Flow Proposals Ledger](./assets/flow_proposals.png)

### Enterprise Off-Peak Compute & Power Inventory (`Sellers` Tab)
Browse live off-peak enterprise compute slots (`Confidential VMs`, `NVIDIA L4`, `A100`, `Google Cloud TPU v5e`, `Intel Xeon`) offered by host enterprises with discounted off-peak pricing and compliance policies:

![Flow Sellers Inventory](./assets/flow_sellers.png)

---

## 🏛️ System Architecture

```
                       ┌───────────────────────────────────────────┐
                       │           Frontier AI Labs                │
                       │ (CenAI Quant, LaprusAI, OpenSynth)        │
                       └─────────────────────┬─────────────────────┘
                                             │ 100 Stratified Proposals
                                             │ (Days 1–10, Tiers 1–10)
                                             ▼
                       ┌───────────────────────────────────────────┐
                       │      Flow Dispatcher Agent                │
                       │ (Matchmaker: Carbon, Capacity, Price)     │
                       └─────────────────────┬─────────────────────┘
                                             │ Place Provisional Hold
                                             ▼
 ┌─────────────────────────────────────────────────────────────────────────────────┐
 │                   Google Cloud Run Commitment Ledger Service                    │
 │                                                                                 │
 │   [AVAILABLE] ──────> [SECURITY_HOLD] ──────> [COMMITTED] / [REJECTED]          │
 │                              │                       or [ESCALATED]             │
 └──────────────────────────────┼──────────────────────────────────────────────────┘
                                │ Sequential 2-Officer Review + Deliberation
                                ▼
                       ┌───────────────────────────────────────────┐
                       │     Security Taskforce Council Agent      │
                       │  Officer 1 ──> Officer 2 ──> Deliberation │
                       │  Models: Gemini 3.8/3.7 Flash,            │
                       │          Claude Opus 5, Claude Sonnet 5   │
                       │  Personas: 32 Big Five (OCEAN) + Neutral  │
                       └─────────────────────┬─────────────────────┘
                                             │ Consensus Verdict
                                             ▼
                       ┌───────────────────────────────────────────┐
                       │   SHA-256 Cryptographic Receipt Chain     │
                       │       (Immutable Tamper-Evident Ledger)   │
                       └───────────────────────────────────────────┘
```

---

## 🔬 Key Capabilities & Research Benchmark Design

### 1. 100-Contract Stratified Benchmark Catalog (`flow/contract_catalog.py`)
Flow uses a **100-contract stratified catalog** spanning **10 Market Days** (10 proposals per day) as its sole workload catalog:
- **Balanced 50/50 Ground Truth & Strict Feature Counterbalancing**:
  - **50 Benign (`ground_truth_safe=True`)**: Risk Tiers **1–5** (10 contracts per tier), progressing from standard enterprise batch workloads (Tiers 1–3) to compliance-adjacent dual-use security/cryptographic and low-level systems workloads (Tiers 4–5).
  - **50 Adversarial (`ground_truth_safe=False`)**: Risk Tiers **6–10** (10 contracts per tier), spanning regulatory/data-residency drift on `PCI-DSS` hosts (Tier 6), runtime dynamic code injection with external package fetching (Tier 7), ticket-framed privileged capability requests (Tier 8), mutable container tags with cross-region object sync (Tier 9), and privileged container/host namespace escapes (Tier 10) across 8 formal threat taxonomy vectors.
  - **Zero Single-Feature Shortcuts**: Every `ComputeType` (`GPU_L4`, `GPU_A100`, `GPU_H100`, `CONFIDENTIAL_VM`, `TPU_V5E`, `CPU_STANDARD`), every Host Seller (`Kove Bank` vs. `Stowe Architects`), every Buyer Identity, `gpu_tensorrt` capability (`8/8`), and parenthetical governance reference (`10/10`) is counterbalanced **50% Benign / 50% Adversarial**.
- **Randomized Presentation Order**: Within each simulated market day, the 10 proposals (one from each Risk Tier 1–10) are shuffled before dispatch (`random.Random(seed * 1000 + day)`), and all ground-truth/tier metadata is stripped from prompts so the Security Council evaluates purely on technical and policy merits.
- **Batch Modes**:
  - **Fixed-Sized Batch (100)**: Evaluates all 100 stratified proposals across 10 market days (10/day).
  - **Random Batch (5–15/day)**: Samples 5 to 15 proposals per day to test variable diurnal load.

### 2. 2-Officer Sequential Security Council & 32 Big Five (OCEAN) Personas (`flow/security_taskforce.py`)
- **Supported Models**:
  - `gemini-3.8-flash` (Gemini 3.8 Flash)
  - `gemini-3.7-flash` (Gemini 3.7 Flash)
  - `claude-opus-5` (Claude Opus 5 via Agent Platform Model Garden)
  - `claude-sonnet-5` (Claude Sonnet 5 via Agent Platform Model Garden)
- **32 Big Five (OCEAN) Format C Personas + Neutral**:
  - Supports `Neutral (No Personality)` plus all **32 binary combinations** ($2^5$) of Openness (`O/o`), Conscientiousness (`C/c`), Extraversion (`E/e`), Agreeableness (`A/a`), and Neuroticism (`N/n`)—e.g., `oCeaN (Sentinel)`, `oCEaN (Auditor)`, `OCEaN (Enforcer)`, `OCean (Analyst)`.
  - Uses **Format C** 3-sentence behavioral tendency descriptions (domain-general cognitive dispositions without explicit security instructions) to avoid prompt-level behavioral circularity.
- **Sequential Conditioning & Peer Deliberation**:
  - **Officer 1** evaluates the workload proposal independently (`APPROVE`, `REJECT`, or `ESCALATE`).
  - **Officer 2** evaluates sequentially with visibility into Officer 1's verdict and rationale.
  - **Council Deliberation** synthesizes the debate transcript and issues a joint consensus (`ALLOW`, `DENY`, or `ESCALATE` to the Human Escalation Queue).

### 3. Multi-Project Workspace Isolation & Cloud Storage Persistence
- Organize experiments into isolated **Projects** via the top-navigation selector (`+ New Project`, switch projects, delete projects, or import/export full project state or single-run JSON snapshots).
- New projects start completely empty (0 runs, 0 contracts, 0 escalations), while the Default Project comes pre-seeded with baseline reference runs.
- State is persisted to `projects_state.json` locally and synced to `gs://your-gcp-project-id-flow-data/projects_state.json` on Cloud Run.

### 4. Concurrency & Multi-Threading Model
- **Within a Single Contract**: Strictly **sequential (single-threaded)** (`Officer 1` $\rightarrow$ `Officer 2` $\rightarrow$ `Council Deliberation`) so Officer 2 is conditioned on Officer 1's completed assessment.
- **Across Contracts Within a Market Day**: Multi-threaded via `ThreadPoolExecutor` (`max_workers=3` by default, configurable `1..8` via `--workers` or `/api/simulation/run`), protected by re-entrant locks (`threading.RLock`) on the `CommitmentLedger` to guarantee an unbroken SHA-256 cryptographic receipt chain.
- **HTTP Server & Async Progress Polling**: Runs on `ThreadingHTTPServer` with background simulation execution (`threading.Thread`) so `/api/simulation/status` streams live contract-by-contract progress to the UI.

---

## 🚀 Quick Start

### 1. Download Demo & Set Up Environment

To download only this demo without cloning the entire repository, use `giget`:
```bash
npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/agents/flow-security-agent-team-simulator flow-security-agent-team-simulator
cd flow-security-agent-team-simulator
```

Create and activate a virtual environment, then install dependencies:
```bash
# Optional: create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Ensure your Google Cloud credentials and project ID are set:
```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### 3. Run the CLI and Local Web UI

```bash
# View available commands
python3 flow_cli.py --help

# Start the interactive developer dashboard on port 8090
python3 flow_cli.py serve --port 8090
```
Open [http://localhost:8090](http://localhost:8090) to view the live dashboard.

---

## 🧪 Testing & Verification

### Run Unit Tests
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Run Marketplace Simulation via CLI
```bash
# Run a 10-day (100-contract) simulation using deterministic offline personas
python3 flow_cli.py simulate --days 10 --offline

# Run a live multi-model simulation on Google Cloud Agent Platform
python3 flow_cli.py simulate --days 1 --live --officers "gemini-3.8-flash:neutral,claude-opus-5:neutral"
```

---

## 🌐 Cloud Run Deployment

Deploy the containerized service directly to Google Cloud Run:
```bash
./deploy_flow_agent_platform.sh
```

Live Cloud Run Endpoints:
- **Dashboard UI**: `https://your-flow-service-url.a.run.app/`
- **Health Check**: `https://your-flow-service-url.a.run.app/health`
- **OpenAPI 3.0 Schema**: `https://your-flow-service-url.a.run.app/api/openapi.json`
- **Receipts Chain**: `https://your-flow-service-url.a.run.app/api/receipts`
