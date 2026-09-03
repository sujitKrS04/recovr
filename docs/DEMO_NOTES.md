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

### 2.4 Zero-Storage Token Security & In-Memory Auth (Phase 11)
- **What to show:** Open Browser DevTools → Application tab → show empty `localStorage` and `sessionStorage` while logged in.
- **Script Talking Point (Say on camera):**
  > *"We store short-lived access tokens strictly in memory — never in `localStorage` — specifically to close the XSS token-exfiltration vector. The refresh token lives in an `httpOnly` cookie, so no JavaScript on the page can ever read it by design. (See [`docs/DECISIONS.md #014`](DECISIONS.md#decision-014--access-token-stored-in-js-memory-explicit-xss-tradeoff))."*
- **Why it matters:** Proves institutional fintech security posture. Prevents XSS token theft without degrading session continuity across reloads.

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

---

## 🎬 Demo Note — Landing Page as Pitch Video Opening Beat

> *Navigate to `http://localhost:5173` before starting the screen recording. The landing page is the first thing judges see — it sets the tone.*

### What's on screen
- **Headline + problem statement**: "Stop losing revenue to failed payments." One sentence underneath explaining what Recovr does.
- **Live uplift card** (centre-stage): Shows real values pulled from `GET /api/summary` — the `+X.X pts uplift vs baseline` and `₹XX,XXX recovered` numbers. **This number is never hardcoded.** If no batch has been run yet, the card shows a prompt to run the first batch. If a batch has been run, it reflects the actual pipeline output from the database.
- **4-step loop row**: Detect → Classify → Decide → Recover, with per-step icons explaining the pipeline at a glance.

### What to say while it's on screen
> *"Every Indian merchant silently loses revenue to failed payments every day. Most teams run blind retries and write off the rest. Recovr is an autonomous recovery agent that intercepts every failed transaction, classifies the root cause with a hybrid rules-plus-LLM engine, and routes each one to the highest-confidence recovery action — with a compliance gate that never auto-retries fraud and never contacts DND customers. The number you see here — ₹[X] recovered, [X] percentage points above a naive retry baseline — is live. It comes from the database. It is not a mock."*

### Why it matters for the demo
The uplift card being live (not hardcoded) is a credibility signal. If a judge refreshes the page or runs the batch themselves and sees the number change, it proves the system is real. Mention this explicitly: **"That number updates every time a batch runs."**

### Transition
Click **"Open dashboard"** → route to `/dashboard` with the AppShell, sidebar, and KPI cards. No dead ends, no loading screens.

---

## 🔐 Demo Note — Login/Signup Flow and RBAC as Build Quality + AI Judgment Proof Point

> *Demonstrate this after the dashboard run — after judges have seen the batch work — to show the system is multi-tenant and permission-enforced.*

### What to show

**Step 1 — Sign in as admin (Acme Corp)**
- Navigate to `/login`. Show the login form. Sign in as `admin@acme.com`.
- The header shows the user pill: `admin@acme.com · admin` with a purple "admin" role badge.
- All controls are visible: "Run Batch", "Simulate Failure", and review action buttons in the Review Queue.

**Step 2 — Sign out and sign in as viewer**
- Click the user pill dropdown → "Sign out".
- Sign in as `viewer@acme.com` (viewer role).
- The header shows the user pill with a grey "viewer" role badge.
- **The "Run Batch" button is gone from the header.** The review action buttons (Approve / Mark as Fraud / Dismiss) are gone from the Review Queue. The dashboard is read-only.

**Step 3 — Try to call the API directly (optional, for a technical audience)**
- Open browser devtools → Network → send a raw `POST http://localhost:8000/api/run-batch` with the viewer's access token as `Authorization: Bearer <token>`.
- The response is **HTTP 403 Forbidden**: `{"detail": "Insufficient permissions"}`.
- This proves the enforcement is server-side, not cosmetic.

### What to say
> *"This isn't frontend UI hiding. The 'Run Batch' button disappears for a viewer because the backend `POST /api/run-batch` endpoint requires the `admin` role and returns HTTP 403 if you call it with a viewer token — even directly via curl. The frontend reflects server permissions; it doesn't define them. Roles are enforced at the API boundary."*

### Why this is a Build Quality + AI Judgment proof point
- **Build Quality**: Proper server-enforced RBAC in a fintech system is table stakes. Showing that the API returns 403 — not just that a button is hidden — demonstrates the system is architecturally correct, not cosmetically role-aware.
- **AI Judgment**: The `analyst` role can see and action the Review Queue (where the AI has escalated uncertain transactions for human review). The `viewer` role can observe but not act. The permission model maps directly to the AI's own confidence gating — the AI escalates, a human analyst decides. The RBAC enforces that only the right human can act on the AI's escalations.

### Multi-org isolation demo (optional, ~30 seconds)
- Sign out of Acme Corp. Sign up as a new org (e.g., "Globex Inc"). Run the batch for Globex.
- Navigate to `/dashboard` — the KPI cards show only Globex transactions. The Live Feed streams only Globex events. Switch back to Acme — Acme's data is completely separate.
- One sentence: *"Every org is fully isolated. Acme Corp never sees Globex's transactions, receipts, or recovery events."*
