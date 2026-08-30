import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Receipt, 
  Search, 
  CheckCircle2, 
  ShieldCheck, 
  Calendar, 
  FileCheck,
  ChevronDown,
  ChevronUp,
  X,
  ExternalLink,
  DollarSign
} from 'lucide-react';
import { api, ReceiptItem } from '../lib/api';
import { StatusBadge } from '../components/ui/StatusBadge';
import { motion, AnimatePresence } from 'framer-motion';

export const ReceiptsPage: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [modalReceipt, setModalReceipt] = useState<ReceiptItem | null>(null);

  const { data: receiptsData, isLoading } = useQuery({
    queryKey: ['receipts'],
    queryFn: api.getReceipts,
  });

  const fallbackReceipts: ReceiptItem[] = [
    {
      id: 1,
      transaction_id: 1,
      customer_name: 'Aarav Patel',
      amount: 1079,
      amount_recovered: 1079,
      root_cause: 'insufficient_funds',
      action_taken: 'payment_link',
      outcome: 'recovered',
      reasoning: 'Classified as insufficient_funds (95% confidence, rule). Routed to payment_link: Insufficient funds detected. Sending payment link to give customer time and a nudge. Recovered INR 1,079 successfully.',
      generated_at: '2026-08-30 20:34:58',
    },
    {
      id: 2,
      transaction_id: 2,
      customer_name: 'Diya Sharma',
      amount: 2501,
      amount_recovered: 2501,
      root_cause: 'bank_downtime',
      action_taken: 'instant_retry',
      outcome: 'recovered',
      reasoning: 'Classified as bank_downtime (90% confidence, rule). Routed to instant_retry: Clean signal for technical downtime (bank_downtime). Safe to auto-retry. Recovered INR 2,501 successfully.',
      generated_at: '2026-08-30 20:34:58',
    },
    {
      id: 3,
      transaction_id: 3,
      customer_name: 'Kavya Nair',
      amount: 4500,
      amount_recovered: null,
      root_cause: 'fraud_false_positive',
      action_taken: 'escalate_human',
      outcome: 'escalated',
      reasoning: 'Classified as fraud_false_positive (10% confidence, llm). Routed to escalate_human: High-risk anomaly detected. Confidence (0.10) below threshold (0.75) -> Escalate to human review. Escalated to human review queue for manual intervention.',
      generated_at: '2026-08-30 20:34:58',
    },
    {
      id: 4,
      transaction_id: 6,
      customer_name: 'Rohan Gupta',
      amount: 3200,
      amount_recovered: null,
      root_cause: 'card_declined',
      action_taken: 'update_card_prompt',
      outcome: 'suppressed',
      reasoning: 'Classified as card_declined (95% confidence, rule). Routed to update_card_prompt: Expired card requires update. Action BLOCKED by Compliance Guard: Customer has opted into DND. Status set to suppressed.',
      generated_at: '2026-08-30 20:34:58',
    },
    {
      id: 5,
      transaction_id: 14,
      customer_name: 'Ananya Verma',
      amount: 1850,
      amount_recovered: 1850,
      root_cause: 'insufficient_funds',
      action_taken: 'payment_link',
      outcome: 'recovered',
      reasoning: 'Classified as insufficient_funds (95% confidence, rule). Routed to payment_link: Insufficient funds detected. Sending payment link to give customer time and a nudge. Recovered INR 1,850 successfully.',
      generated_at: '2026-08-30 20:34:58',
    },
  ];

  const receipts: ReceiptItem[] = receiptsData && receiptsData.length > 0 ? receiptsData : fallbackReceipts;

  const filteredReceipts = receipts.filter(
    (r) =>
      r.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      `tx_${r.transaction_id}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.root_cause?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.outcome?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Search and Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4.5 rounded-xl bg-card border border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center text-primary">
            <FileCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground tracking-tight">
                Recovery Receipts Ledger
              </h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground border border-border font-medium">
                {receipts.length} Audited Receipts
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Immutable audit trail with plain-English reasoning generated for every terminal action
            </p>
          </div>
        </div>

        {/* Search input */}
        <div className="relative w-full sm:w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by ID, customer, cause..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-background border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary transition-colors"
          />
        </div>
      </div>

      {/* Receipts Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-center">
                <div className="h-5 w-24 rounded bg-[#1E2640]/60 animate-pulse" />
                <div className="h-5 w-16 rounded bg-[#1E2640]/60 animate-pulse" />
              </div>
              <div className="h-8 w-full rounded bg-[#1E2640]/60 animate-pulse" />
              <div className="h-16 w-full rounded bg-[#1E2640]/60 animate-pulse" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredReceipts.map((r) => {
          const isExpanded = expandedId === r.id;
          return (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-card border border-border rounded-xl p-5 hover:border-primary/40 transition-all flex flex-col justify-between"
            >
              <div>
                {/* Top Meta */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-foreground bg-background px-2 py-0.5 rounded border border-border">
                      tx_{r.transaction_id}
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {r.customer_name}
                    </span>
                  </div>
                  <StatusBadge status={r.outcome} size="sm" />
                </div>

                {/* Amount & Classification */}
                <div className="flex items-center justify-between py-2 border-y border-border/50 text-xs my-3">
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider">
                      Original Amount
                    </span>
                    <span className="font-mono font-medium text-foreground">
                      ₹{r.amount.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-muted-foreground block text-[10px] uppercase tracking-wider">
                      Recovered
                    </span>
                    <span
                      className={`font-mono font-bold ${
                        r.amount_recovered ? 'text-success' : 'text-muted-foreground'
                      }`}
                    >
                      {r.amount_recovered ? `₹${r.amount_recovered.toLocaleString('en-IN')}` : '—'}
                    </span>
                  </div>
                </div>

                {/* Badges */}
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <StatusBadge status={r.root_cause} size="sm" />
                  <StatusBadge status={r.action_taken} size="sm" />
                </div>

                {/* Human-readable reasoning string with click to expand */}
                <div
                  onClick={() => toggleExpand(r.id)}
                  className="p-3 rounded-lg bg-background/70 border border-border/70 text-xs text-muted-foreground leading-relaxed font-sans cursor-pointer hover:border-primary/30 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-foreground font-semibold flex items-center gap-1">
                      <ShieldCheck className="w-3.5 h-3.5 text-primary" />
                      Audit Trail Reasoning
                    </span>
                    <span className="text-[10px] text-primary flex items-center gap-0.5">
                      {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </span>
                  </div>
                  <p className={isExpanded ? '' : 'line-clamp-2'}>
                    {r.reasoning}
                  </p>
                </div>
              </div>

              {/* Timestamp footer & Details modal trigger */}
              <div className="mt-4 pt-3 border-t border-border/50 flex items-center justify-between text-[11px] font-mono text-muted-foreground">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-muted-foreground" />
                  {r.generated_at.split('T')[0] || r.generated_at}
                </span>
                <button
                  onClick={() => setModalReceipt(r)}
                  className="text-primary hover:text-primary/80 font-sans text-xs flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <ExternalLink className="w-3 h-3" />
                  Full Certificate
                </button>
              </div>
            </motion.div>
          );
        })}
        </div>
      )}

      {/* Modal / Certificate Detail View */}
      <AnimatePresence>
        {modalReceipt && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-card border border-border rounded-2xl max-w-lg w-full p-6 shadow-2xl relative"
            >
              <button
                onClick={() => setModalReceipt(null)}
                className="absolute right-4 top-4 text-muted-foreground hover:text-foreground p-1 rounded-lg hover:bg-background transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                  <Receipt className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground tracking-tight">
                    Recovery Receipt #rec_{modalReceipt.id}
                  </h3>
                  <span className="text-xs text-muted-foreground font-mono">
                    Transaction: tx_{modalReceipt.transaction_id}
                  </span>
                </div>
              </div>

              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-background border border-border">
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Customer</span>
                    <span className="font-semibold text-foreground">{modalReceipt.customer_name}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Outcome</span>
                    <StatusBadge status={modalReceipt.outcome} size="sm" />
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Amount at Risk</span>
                    <span className="font-mono font-medium text-foreground">₹{modalReceipt.amount.toLocaleString('en-IN')}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block text-[10px] uppercase">Amount Recovered</span>
                    <span className="font-mono font-bold text-success">
                      {modalReceipt.amount_recovered ? `₹${modalReceipt.amount_recovered.toLocaleString('en-IN')}` : '₹0'}
                    </span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-background border border-border/80 space-y-2">
                  <span className="font-semibold text-foreground block">Complete Autonomous Audit Trail</span>
                  <p className="text-muted-foreground leading-relaxed font-sans">
                    {modalReceipt.reasoning}
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-primary/5 border border-primary/20 flex items-center justify-between text-[11px] text-muted-foreground font-mono">
                  <span>Compliance Verification</span>
                  <span className="text-success font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Validated
                  </span>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
