/**
 * api.ts — Recovr API client
 *
 * Cross-origin cookie configuration:
 * - credentials: 'include' is set on EVERY fetch call so the browser sends
 *   the refresh_token httpOnly cookie even across ports (5173 → 8000).
 * - This is critical for the /api/auth/refresh flow: if credentials is
 *   omitted the cookie is never sent and refresh silently fails with 401.
 * - authFetch automatically retries once with a fresh access token when
 *   the API returns 401, then fails hard if the refresh also fails.
 */

const API_BASE = 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Data interfaces
// ---------------------------------------------------------------------------

export interface SummaryData {
  total_at_risk: number;
  total_recovered: number;
  total_recovering: number;
  recovery_rate: number;
  baseline_recovery_rate: number;
  categories: Record<
    string,
    {
      total: number;
      recovered: number;
      recovering: number;
      at_risk: number;
    }
  >;
}

export interface TransactionItem {
  id: number;
  external_payment_id: string;
  customer_name: string;
  amount: number;
  currency: string;
  status: string;
  failure_reason: string;
  category: string | null;
  action: string | null;
  auto_executed: boolean | null;
  retry_count: number;
}

export interface ReceiptItem {
  id: number;
  transaction_id: number;
  customer_name: string;
  amount: number;
  root_cause: string;
  action_taken: string;
  reasoning: string;
  amount_recovered: number | null;
  outcome: string;
  generated_at: string;
}

export interface ReviewQueueItem {
  transaction_id: number;
  customer_name: string;
  amount: number;
  failure_reason: string;
  category: string;
  confidence: number;
  decision_reasoning: string;
}

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  org_id: number;
  org_name: string;
  org_slug: string;
}

// ---------------------------------------------------------------------------
// Token store — kept in memory (not localStorage) for XSS safety.
// The refresh token lives only in the httpOnly cookie managed by the backend.
// ---------------------------------------------------------------------------

let _accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  _accessToken = token;
}

export function getAccessToken(): string | null {
  return _accessToken;
}

// ---------------------------------------------------------------------------
// authFetch — authenticated fetch with automatic silent refresh
//
// credentials: 'include' is set globally here so the httpOnly refresh_token
// cookie is sent on EVERY request, including POST /api/auth/refresh.
// Without this option the browser blocks the cookie in cross-origin calls.
// ---------------------------------------------------------------------------

let _isRefreshing = false;
let _refreshWaiters: Array<(token: string | null) => void> = [];

async function _doRefresh(): Promise<string | null> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // ← MUST be 'include' to send the httpOnly cookie
    });
    if (!res.ok) {
      setAccessToken(null);
      return null;
    }
    const data = await res.json();
    setAccessToken(data.access_token);
    return data.access_token;
  } catch {
    setAccessToken(null);
    return null;
  }
}

export async function authFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const doFetch = (token: string | null) =>
    fetch(`${API_BASE}${input}`, {
      ...init,
      credentials: 'include', // ← credentials: 'include' on every call
      headers: {
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

  const res = await doFetch(_accessToken);

  // If 401, attempt one silent refresh, then retry
  if (res.status === 401) {
    if (_isRefreshing) {
      // Another refresh is in flight — queue this request
      const newToken = await new Promise<string | null>((resolve) => {
        _refreshWaiters.push(resolve);
      });
      return doFetch(newToken);
    }

    _isRefreshing = true;
    const newToken = await _doRefresh();
    _isRefreshing = false;

    // Resolve all queued requests
    _refreshWaiters.forEach((resolve) => resolve(newToken));
    _refreshWaiters = [];

    if (!newToken) {
      // Refresh failed → propagate the 401 so callers can redirect to login
      return res;
    }
    return doFetch(newToken);
  }

  return res;
}

// ---------------------------------------------------------------------------
// Auth API methods
// ---------------------------------------------------------------------------

export const authApi = {
  async signup(body: {
    org_name: string;
    org_slug: string;
    full_name: string;
    email: string;
    password: string;
  }): Promise<{ access_token: string }> {
    const res = await fetch(`${API_BASE}/api/auth/signup`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? 'Signup failed');
    }
    return res.json();
  },

  async login(email: string, password: string): Promise<{ access_token: string }> {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? 'Login failed');
    }
    return res.json();
  },

  async refresh(): Promise<string | null> {
    return _doRefresh();
  },

  async logout(): Promise<void> {
    await authFetch('/api/auth/logout', { method: 'POST' });
    setAccessToken(null);
  },

  async me(): Promise<AuthUser> {
    const res = await authFetch('/api/auth/me');
    if (!res.ok) throw new Error('Not authenticated');
    return res.json();
  },
};

// ---------------------------------------------------------------------------
// Business API — all calls go through authFetch (credentials + auto-refresh)
// ---------------------------------------------------------------------------

export const api = {
  async getSummary(): Promise<SummaryData> {
    const res = await authFetch('/api/summary');
    if (!res.ok) throw new Error('Failed to fetch summary');
    return res.json();
  },

  async getTransactions(
    status?: string,
    category?: string,
    limit?: number,
    offset?: number,
  ): Promise<TransactionItem[]> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (category) params.append('category', category);
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    const res = await authFetch(`/api/transactions?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch transactions');
    return res.json();
  },

  async getReceipts(): Promise<ReceiptItem[]> {
    const res = await authFetch('/api/receipts');
    if (!res.ok) throw new Error('Failed to fetch receipts');
    return res.json();
  },

  async getReceipt(transactionId: number): Promise<ReceiptItem> {
    const res = await authFetch(`/api/receipts/${transactionId}`);
    if (!res.ok) throw new Error('Failed to fetch receipt');
    return res.json();
  },

  async getReviewQueue(): Promise<ReviewQueueItem[]> {
    const res = await authFetch('/api/review-queue');
    if (!res.ok) throw new Error('Failed to fetch review queue');
    return res.json();
  },

  async runBatch(): Promise<{ message: string }> {
    const res = await authFetch('/api/run-batch', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to trigger batch run');
    return res.json();
  },

  async simulateFailure(): Promise<{ message: string }> {
    const res = await authFetch('/api/simulate-failure', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to simulate failure');
    return res.json();
  },

  async simulatePaymentConfirmation(transactionId: number): Promise<{ message: string }> {
    const res = await authFetch(`/api/simulate-payment-confirmation/${transactionId}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to simulate payment confirmation');
    return res.json();
  },
};
