const API_BASE = 'http://localhost:8000';

export interface SummaryData {
  total_at_risk: number;
  total_recovered: number;
  recovery_rate: number;
  baseline_recovery_rate: number;
  categories: Record<
    string,
    {
      total: number;
      recovered: number;
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

export const api = {
  async getSummary(): Promise<SummaryData> {
    const res = await fetch(`${API_BASE}/api/summary`);
    if (!res.ok) throw new Error('Failed to fetch summary');
    return res.json();
  },

  async getTransactions(status?: string, category?: string, limit?: number, offset?: number): Promise<TransactionItem[]> {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (category) params.append('category', category);
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());
    const res = await fetch(`${API_BASE}/api/transactions?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch transactions');
    return res.json();
  },

  async getReceipts(): Promise<ReceiptItem[]> {
    const res = await fetch(`${API_BASE}/api/receipts`);
    if (!res.ok) throw new Error('Failed to fetch receipts');
    return res.json();
  },

  async getReceipt(transactionId: number): Promise<ReceiptItem> {
    const res = await fetch(`${API_BASE}/api/receipts/${transactionId}`);
    if (!res.ok) throw new Error('Failed to fetch receipt');
    return res.json();
  },

  async getReviewQueue(): Promise<ReviewQueueItem[]> {
    const res = await fetch(`${API_BASE}/api/review-queue`);
    if (!res.ok) throw new Error('Failed to fetch review queue');
    return res.json();
  },

  async runBatch(): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/api/run-batch`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to trigger batch run');
    return res.json();
  },

  async simulateFailure(): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/api/simulate-failure`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to simulate failure');
    return res.json();
  },
};
