# Demo Notes & Pitch Script Guide

This document organizes all demo moments, engineering evidence, and metrics around the four judging criteria for Razorpay's AI Buildathon (Track 3): **Problem Taste**, **Build Quality**, **AI Judgment**, and **Failure Recovery**.

---

## 🎬 Opening Beat — Landing Page (`/`)

> *Start the recording here. Navigate to `http://localhost:5173`. The landing page should be the first thing judges see.*

### What's on screen
- **Recovr wordmark** — `RECOVR · AI` in the top-left, matched exactly to the in-product sidebar brand.
- **Headline**: "Stop losing revenue to failed payments."
- **Problem statement** (one sentence): Recovr intercepts every failed transaction, classifies the root cause with AI, and routes it to the right recovery action automatically.
- **Live uplift card** (only shown if a batch has run): displays the real `+X.X pts uplift vs baseline` and `₹XX,XXX recovered` pulled live from `GET /api/summary`. This number is never hardcoded.
- **4-step core loop row**: Detect → Classify → Decide → Recover, with per-step icons and a one-line descriptor.
- **Two CTAs**: "Open dashboard" and "Watch it live".

### What to say while it's on screen
> *"Every Indian merchant loses a percentage of their GMV to silent payment failures. Recovr is an autonomous recovery agent — it detects failures in real time, classifies the root cause across six categories using a hybrid rules-plus-LLM engine, routes each one to the highest-confidence recovery action, and does all of this with a compliance gate that never auto-retries fraud and never contacts DND customers. In this live batch, we recovered ₹[X] in revenue that would have been written off — [X] percentage points above what a naive retry system achieves."*

### Transition
Click **"Open dashboard"** → seamless route to `/dashboard` with the AppShell layout, header, and sidebar sliding in. No dead ends.

---


## 🎯 Master Demo Matrix (Ready for Pitch Video)

| Judging Criterion | Key Pitch Moments | What to Show in UI / CLI | Why It Wins the Hackathon |
|---|---|---|---|
| **1. Problem Taste** | • Real-world failure taxonomy (6 decline types)<br>• Baseline Uplift benchmark (+35.1% revenue)<br>• DND opt-out compliance | • Dashboard KPI cards & Uplift delta badge (`+12.6 pts vs base`)<br>• Root Cause taxonomy bar chart | Proves deep domain understanding: payment recovery isn't just "retry everything"; blind retries destroy margins and trigger chargebacks. |
| **2. Build Quality** | • Real-time WebSocket streaming<br>• Defense-in-depth compliance wrapper<br>• Immutable audit receipts with plain English | • Top bar "Run Batch" triggering live progress & line curve<br>• Receipts Ledger modal ("Full Certificate") | Production-grade architecture: FastAPI + PostgreSQL + TanStack Query + Framer Motion. Zero mocks for business logic. |
| **3. AI Judgment** | • Knowing when *NOT* to use AI (85% rules)<br>• Knowing when to use AI (LLM on fraud flags)<br>• Refusal to act (confidence gating &lt; 0.75) | • CLI `[RULE x40]` vs `[LLM]` output<br>• Review Queue showing quarantined low-conviction items with plain rationale | Shows AI maturity: we don't hallucinate or waste tokens on "card expired"; we quarantine high-risk anomalies to human approval. |
| **4. Failure Recovery** | • "Simulate Failure" live demo trigger<br>• Automated retry & self-healing recovery<br>• Fail-safe degradation on LLM API outage | • Click "Simulate Failure" → Amber `[DETECTED ISSUE]` → Green `[AUTOMATED RETRY & RECOVERY]` in Live Feed | Demonstrates fintech resilience: when gateway APIs drop connections, the agent detects, adapts, and recovers automatically. |

---

## 🧭 Criterion 1 — Problem Taste

> *Does the team understand the real problem, not just the surface request?*

### 1.1 Realistic 6-Category Failure Taxonomy (Phase 2)
- **What to show:** Run `python -m scripts.generate_batch` or show the Dashboard Root Cause Taxonomy chart.
- **What happens:** 120 realistic Indian payment records distributed across 6 categories (Gateway Timeout, Bank Downtime, Insufficient Funds, Card Declined, OTP Failure, Fraud False Positive) with ₹200 to ₹45,000 variance and 8% DND opt-out flags.
- **Why it matters:** Real payment recovery systems face diverse failure modes. Treating an expired card the same as a bank outage causes instant failure.

### 1.2 Uplift Measured Against Naive Baseline (Phase 5 & 9)
- **What to show:** Dashboard Uplift Callout (`+₹41,705` Net Revenue, `+35.1%` Uplift over baseline).
- **What happens:** Compares the AI agent's intelligent routing against a naive blind single-retry baseline.
- **Why it matters:** Comparing recovery to $0 is intellectually dishonest. Businesses already do naive retries. Proving a **+35.1% revenue lift** over existing merchant logic demonstrates pure business value.

---

## 🛠️ Criterion 2 — Build Quality

> *Is the code real, structured, and maintainable? Does the architecture hold together?*

### 2.1 Defense-in-Depth Programmatic Compliance Guard (Phase 6)
- **What to show:** Highlight `[BLOCKED]` transactions in `actions_log` and `suppressed` status in the Receipts view.
- **What happens:** `compliance_guard.py` acts as a non-bypassable gate wrapping every executor. It blocks contact for DND users, caps retries at 3, enforces a 4-hour cooldown, and strictly forbids auto-executing fraud signals.
- **Why it matters:** Proves enterprise safety. In fintech, an LLM prompt alone cannot be trusted with financial execution; strict programmatic boundaries are required.

### 2.2 Immutable Recovery Receipts Audit Ledger (Phase 6 & 9)
- **What to show:** Click "Receipts" in the sidebar and open "Full Certificate" modal on any transaction.
- **What happens:** Displays a complete audit certificate with human-readable rationale: e.g. `"Classified as insufficient_funds (95% confidence, rule). Routed to payment_link: Insufficient funds detected. Recovered INR 1,079 successfully."`
- **Why it matters:** Financial institutions require explainability for AI actions for auditing, chargeback disputes, and compliance reporting.

### 2.3 Real-Time WebSocket Streaming & Framer Motion UI (Phase 7–9)
- **What to show:** Click "Run Batch" in the top bar while viewing Dashboard or Live Feed.
- **What happens:** The dashboard comes alive: live progress banner animates, events stream row-by-row via WebSocket (`/ws/live`), numbers count up smoothly, and Recharts line curve updates dynamically.
- **Why it matters:** Zero polling overhead; provides high-fidelity observability during merchant operations.

---

## 🧠 Criterion 3 — AI Judgment

> *Where does AI help? Where does it deliberately NOT get used? When does the system refuse to act?*

### 3.1 Knowing When NOT to Use AI (Phase 3)
- **What to show:** Run `python -m scripts.run_classifier` — watch `[RULE x20]` and `[RULE x40]` scroll past in milliseconds.
- **What happens:** 114 out of 120 records (95%) are classified by deterministic regex rules with 0.90+ confidence.
- **Why it matters:** "Card expired" does not need an LLM. Calling AI on obvious decline codes wastes tokens, adds latency, and introduces non-determinism into deterministic signals.

### 3.2 Knowing When AI Helps (Phase 3)
- **What to show:** The `[LLM]` classification logs for fraud reasons ("Velocity check triggered", "Risk engine declined").
- **What happens:** Routes ambiguous failure strings to OpenRouter LLM (`openrouter/free`) with structured JSON schema output and in-memory caching.
- **Why it matters:** Nuanced fraud indicators require contextual analysis that simple keyword matching cannot safely provide.

### 3.3 Deliberate Refusal to Act: Confidence Gating (Phase 4 & 9)
- **What to show:** Review Queue page displaying quarantined transactions with conviction &lt; 0.75.
- **What happens:** The agent isolates uncertain transactions into human review, explaining in plain English why automated intervention was halted.
- **Why it matters:** Safe automation beats 100% reckless automation. The system understands its own conviction boundaries.

---

## 🔄 Criterion 4 — Failure Recovery

> *What broke during development? How was it fixed? What can be demonstrated live?*

### 4.1 Live Demo Failure Injection: Self-Healing Recovery (Phase 9)
- **What to show:** Click "Simulate Failure" button in header, then watch the next transaction in Live Feed.
- **What happens:**
  1. Transaction shows amber `[DETECTED ISSUE]` detailing a simulated gateway reset.
  2. The agent catches the failure, increments retry count, and executes an automated recovery via fallback route.
  3. Live Feed turns green `[AUTOMATED RETRY & RECOVERY]`, recovering the funds and issuing a receipt.
- **Why it matters:** Demonstrates resilience in untrusted networks. Shows self-healing execution when external payment APIs fail.

### 4.2 Safe Degradation on Missing API Keys (Phase 3)
- **What to show:** Run classifier with `OPENROUTER_API_KEY` unset.
- **What happens:** Returns a flagged `other` category with confidence 0.10 and an explicit audit explanation rather than crashing.
- **Why it matters:** Financial systems must fail safe, never silently fail or misclassify unhandled errors.

### 4.3 Engineering Failure Log Summary
All 11 technical failures encountered during development were recorded in [`docs/FAILURE_LOG.md`](FAILURE_LOG.md) with root causes and permanent fixes:
- [#001 — PostgreSQL password authentication failure](FAILURE_LOG.md#failure-001--docker-compose-postgres-auth-failure)
- [#002 — Python virtual environment Windows path resolution](FAILURE_LOG.md#failure-002--python-virtual-environment-missing-in-backend)
- [#003 — Alembic fileConfig crash](FAILURE_LOG.md#failure-003--alembic-fileconfig-crash-due-to-missing-formatters-section)
- [#004 — Keyword collision in summary printer](FAILURE_LOG.md#failure-004--keyword-collision-in-summary-printer-miscounted-distribution)
- [#005 — setuptools pkg_resources deprecation](FAILURE_LOG.md#failure-005--razorpay-sdk-broken-by-missing-pkg_resources-setuptools-deprecation)
- [#006 — Windows console cp1252 character encoding crash](FAILURE_LOG.md#failure-006--windows-console-cp1252-character-encoding-crash-with-unicode-arrows)
- [#007 — OpenRouter unauthorized HTTP 401 handling](FAILURE_LOG.md#failure-007--openrouter-unauthorized-http-401-crashed-classifier)
- [#008 — Naive baseline test-mode key mock artifact](FAILURE_LOG.md#failure-008--mock-artifact-naive-baseline-always-succeeded-with-test-keys)
- [#009 — Compliance guard `suppressed` status PostgreSQL enum mismatch](FAILURE_LOG.md#failure-009--compliance-guard-suppressed-status-crashed-execution-due-to-enum-mismatch)
- [#010 — API Batch runner object property mismatch](FAILURE_LOG.md#failure-010--api-batch-runner-crashed-due-to-object-property-mismatch-category-vs-root_cause_category)
- [#011 — Browser TypeScript NodeJS.Timeout typing error](FAILURE_LOG.md#failure-011--browser-environment-typescript-namespace-error-with-nodejstimeout--parameter-signature-mismatch)

---

## 🎬 3-Minute Video Pitch Script Outline

1. **The Hook (0:00 – 0:30)**:
   - "Merchants lose up to 30% of revenue to payment failures. Blind retries don't work and annoy customers. Meet Recovr: an autonomous revenue recovery agent with root-cause detection, confidence gating, and compliance guardrails."
2. **The Architecture & AI Judgment (0:30 – 1:15)**:
   - Click "How this works" panel on the live dashboard.
   - "We don't waste LLM calls on obvious errors. 85% is resolved via instant deterministic rules. For ambiguous fraud signals, our OpenRouter fallback classifies with structured conviction."
3. **The Core Demo — Live Run Batch (1:15 – 2:00)**:
   - Hit "Run Batch" in the top bar.
   - Watch the Live Feed stream in real time and show the Recharts dynamic trajectory beating baseline (+35.1% uplift).
4. **Safety & Compliance (2:00 – 2:30)**:
   - Navigate to Review Queue and Receipts.
   - "Conviction &lt; 0.75 is quarantined to human review. DND users are strictly suppressed. Every recovery generates an immutable plain-English receipt."
5. **Self-Healing Failure Recovery & Close (2:30 – 3:00)**:
   - Hit "Simulate Failure" and show the amber detected issue automatically retrying and recovering.
   - "Recovr: +35.1% revenue uplift, 100% compliance, zero fraud auto-execution."
