# Recovr — Autonomous Revenue Recovery Agent

> **AI-Powered Revenue Recovery with Multi-Tenant Auth, RBAC, Confidence-Gated Interventions, Root Cause Detection & Defense-in-Depth Compliance for Razorpay's AI Buildathon (Track 3)**

[![Live Demo](https://img.shields.io/badge/Demo-Live%20Stream-635BFF?style=for-the-badge&logo=fastapi)](http://localhost:5173)
[![Uplift](https://img.shields.io/badge/Revenue%20Uplift-%2B35.1%25-00D4A0?style=for-the-badge)](docs/DEMO_NOTES.md)
[![Safety Score](https://img.shields.io/badge/Compliance%20Safety-100%25-00D4A0?style=for-the-badge)](docs/DECISIONS.md)
[![Multi-Tenant RBAC](https://img.shields.io/badge/Auth-JWT%20%2B%20RBAC%20(3%20Roles)-635BFF?style=for-the-badge)](docs/DECISIONS.md)

---

## 🎯 Problem Statement

Online merchants lose **15% to 30% of their top-line revenue** to failed transactions (insufficient funds, bank downtime, card declines, false-positive fraud flags). Naive payment recovery systems blindly retry every failed charge, leading to:
1. **Wasted Gateway Fees & Exhaustion**: Retrying hard declines like expired cards or insufficient funds immediately is futile and annoys customers.
2. **Catastrophic False Positive Retries**: Retrying fraud-adjacent signals risks chargebacks, network fines, and regulatory non-compliance.
3. **Zero Explainability**: Merchants have no visibility into *why* a payment failed or *why* a recovery action was selected.

**Recovr** solves this with an **autonomous, multi-tenant, confidence-gated recovery agent**:
- **Multi-Tenant & RBAC Protected**: Complete organization isolation (`org_id` scoped transactions, WebSocket streams, receipts) with 3-tier role enforcement (`admin`, `analyst`, `viewer`) at the server API layer.
- **Two-Stage Classifier**: High-speed deterministic regex rules (85%) + OpenRouter LLM fallback (15%).
- **Confidence Gating**: High conviction (&ge; 0.75) triggers automated Razorpay execution (Payment Links, Instant Retries, Card Update Prompts); low conviction (&lt; 0.75) or fraud flags route to Human Review.
- **Defense-in-Depth Compliance Guard**: A non-bypassable programmatic gate enforcing DND suppression, 3-retry maximum cap, and a 4-hour cooldown.
- **Immutable Recovery Receipts**: Human-readable audit certificates generated for every terminal action.
- **Live Landing Page (`/`)**: Dedicated entry beat featuring real-time live uplift metrics calculated from database batch outputs.

---

## 🏗️ Architecture & Pipeline Flow

```mermaid
flowchart TD
    A[Public Landing Page / \nLive Uplift Stats] --> Auth[Auth & RBAC Gate\nJWT + httpOnly Refresh Cookie]
    Auth --> OrgScope[Org-Scoped Context\norg_id Filtering]
    
    OrgScope --> B{Stage 1: Rule-Based Matcher}
    B -- Unambiguous (85%) --> C[Root Cause Identified\nConfidence >= 0.90]
    B -- Ambiguous / Fraud (15%) --> D[Stage 2: OpenRouter LLM Fallback\nfree auto-router + Cache]
    D --> C

    C --> E[Decision Agent\nAction Mapping]
    E --> F{Confidence Gate\nConviction >= 0.75?}
    
    F -- Low Conviction / Fraud Flag --> G[Human Review Queue\nAnalyst+ Action Required]
    F -- High Conviction --> H[Defense-in-Depth Compliance Guard]

    H --> I{Passes Guardrails?\nDND / Retry <= 3 / Cooldown}
    I -- Blocked (DND / Limit) --> J[Suppressed / Exhausted Log]
    I -- Approved (Admin Role Required) --> K[Razorpay API Executor\nTest Mode]

    K --> L[Org WebSocket Stream\n/ws/live?org_id=X]
    G --> L
    J --> L
    K --> M[Immutable Recovery Receipt\nAudit Ledger]
    L --> N[React + Vite Fintech Dashboard]
```

---

## 📊 Benchmark Uplift vs Naive Baseline

In our standardized benchmark run on 120 synthetic Indian merchant transactions (₹3,29,993 total value at risk per org):

| Metric | Naive Blind Retry | Recovr AI Agent | Net Advantage |
|---|---|---|---|
| **Transactions Recovered** | 34 / 120 (28.3%) | **66 / 120 (55.0%)** | **+32 Recovered Transactions** |
| **Total Revenue Recovered** | ₹1,18,741 | **₹1,60,446** | **+₹41,705 Incremental Yield** |
| **Recovery Uplift (%)** | Baseline (0.0%) | **+35.1% Uplift** | **+35.1% Pure Revenue Lift** |
| **Fraud Risk False Positives** | 6 Unsafe Retries | **0 Retries (100% Escalate)** | **Zero Chargeback Risk** |
| **DND Opt-Out Compliance** | 0% Guarded | **100% Suppressed (7 blocked)** | **100% Regulatory Compliance** |

---

## 🚀 Quick Start (Run Locally)

### 1. Prerequisites
- PostgreSQL 16 (Native or Docker)
- Python 3.11+
- Node.js 18+ and npm

### 2. Backend Setup
```bash
cd backend
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # Add OPENROUTER_API_KEY / RAZORPAY test keys

# Initialize Schema and Run Migration
alembic upgrade head

# Seed Demo Organizations & Transactions (Acme Corp & Globex Inc)
python -m scripts.seed_two_orgs

# Start Backend Server
uvicorn app.main:app --reload --port 8000
# Backend API Live at http://localhost:8000/docs
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Frontend Dashboard Live at http://localhost:5173
```

### 4. Demo Login Credentials

Pre-seeded multi-tenant accounts with full role-based access control (RBAC):

| Organization | Email | Password | Role | Permissions |
|---|---|---|---|---|
| **Acme Corp** | `alice@acme.com` *(or `admin@acme.com`)* | `password123` | `admin` | Full control (Run Batch, Review Queue, Settings) |
| **Acme Corp** | `analyst@acme.com` | `password123` | `analyst` | Review Queue actions, Simulate Failure |
| **Acme Corp** | `viewer@acme.com` | `password123` | `viewer` | Read-only observation dashboard |
| **Globex Inc** | `bob@globex.com` *(or `admin@globex.com`)* | `password123` | `admin` | Full control (Globex tenant data isolation) |

---

## 🎥 Pitch Video & Demo Recording

- **Pitch Video:** [Watch Pitch Video (YouTube / Loom) — *Link to be inserted*](https://youtube.com)
- **Live Demo Video (Browser Artifact):** `recovr_final_qa.webp`

---

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.11+, SQLAlchemy, Alembic, PostgreSQL 16, Pydantic v2, Uvicorn, WebSockets, PyJWT, Passlib (bcrypt).
- **Frontend**: Vite, React 18, TypeScript, Tailwind CSS, TanStack Query v5, Framer Motion, Recharts, Lucide Icons.
- **AI Engine**: OpenRouter Free Auto-Router (`openrouter/free`) with in-memory regex caching and exponential backoff.
- **Payment Integration**: Razorpay Python SDK (Test Mode / Mock fallback).

---

## 📑 Engineering Trail & Documentation

- [`docs/FAILURE_LOG.md`](docs/FAILURE_LOG.md) — 16 Technical Failure Log entries with root cause analyses and permanent fixes.
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — 18 Architecture Decision Records (ADRs) detailing design trade-offs.
- [`docs/DEMO_NOTES.md`](docs/DEMO_NOTES.md) — Complete pitch & demo guide mapped to the 4 Hackathon judging criteria (including Landing Page beat & RBAC proof).
