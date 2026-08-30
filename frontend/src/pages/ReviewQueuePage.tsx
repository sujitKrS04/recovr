import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { 
  ShieldAlert, 
  UserCheck, 
  Check, 
  X, 
  AlertTriangle,
  Info,
  Sparkles
} from 'lucide-react';
import { api, ReviewQueueItem } from '../lib/api';
import { StatusBadge } from '../components/ui/StatusBadge';
import { motion } from 'framer-motion';

export const ReviewQueuePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { data: queueData, isLoading } = useQuery({
    queryKey: ['reviewQueue'],
    queryFn: api.getReviewQueue,
  });

  const [handledIds, setHandledIds] = useState<number[]>([]);

  const handleApprove = (txId: number) => {
    setHandledIds((prev) => [...prev, txId]);
  };

  const handleDismiss = (txId: number) => {
    setHandledIds((prev) => [...prev, txId]);
  };

  const initialFallbackItems: ReviewQueueItem[] = [
    {
      transaction_id: 3,
      customer_name: 'Kavya Nair',
      amount: 4500,
      failure_reason: 'Transaction flagged by automated fraud detection engine',
      category: 'fraud_false_positive',
      confidence: 0.10,
      decision_reasoning: 'Fraud-adjacent signal detected. High risk: auto-execution strictly prohibited by defense-in-depth safety guard. Requires manual agent sign-off.',
    },
    {
      transaction_id: 12,
      customer_name: 'Vikram Mehta',
      amount: 14200,
      failure_reason: 'Risk engine declined - unusual spending pattern from new IP',
      category: 'fraud_false_positive',
      confidence: 0.15,
      decision_reasoning: 'Unrecognized anomaly detected. Confidence (0.15) below threshold (0.75) -> Escalate to human operator for verification.',
    },
    {
      transaction_id: 21,
      customer_name: 'Priya Sundaram',
      amount: 38000,
      failure_reason: 'Suspicious activity flag from issuer risk system',
      category: 'fraud_false_positive',
      confidence: 0.10,
      decision_reasoning: 'High-value transaction flagged by bank risk system. Requires operator verification before outreach.',
    },
    {
      transaction_id: 42,
      customer_name: 'Manish Joshi',
      amount: 9200,
      failure_reason: 'Velocity check triggered - multiple attempts across different cards',
      category: 'fraud_false_positive',
      confidence: 0.20,
      decision_reasoning: 'Velocity limit exceeded. Deferring to human review to prevent chargeback risk.',
    },
  ];

  const items: ReviewQueueItem[] = (queueData && queueData.length > 0 ? queueData : initialFallbackItems)
    .filter((item) => !handledIds.includes(item.transaction_id));

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner explaining confidence gating */}
      <div className="p-4.5 rounded-xl bg-card border border-border flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg bg-warning/15 border border-warning/30 flex items-center justify-center text-warning flex-shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground tracking-tight">
                Confidence-Gated Human Review Queue
              </h2>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-warning/20 text-warning border border-warning/30 font-medium">
                {items.length} Pending Actions
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5 max-w-2xl leading-relaxed">
              Transactions routed here when decision conviction is below <span className="text-foreground font-mono font-medium">0.75</span> or flagged with <span className="text-warning font-mono font-medium">fraud-adjacent</span> signals. The autonomous agent deliberately refuses to act on these without human sign-off.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground bg-background px-3 py-2 rounded-lg border border-border flex-shrink-0">
          <Info className="w-4 h-4 text-primary" />
          Gating Rule: &lt; 0.75 Conviction
        </div>
      </div>

      {/* Review Queue Items */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-5 space-y-3">
              <div className="flex justify-between items-center">
                <div className="flex gap-2">
                  <div className="h-5 w-16 rounded bg-[#1E2640]/60 animate-pulse" />
                  <div className="h-5 w-24 rounded bg-[#1E2640]/60 animate-pulse" />
                </div>
                <div className="h-6 w-20 rounded bg-[#1E2640]/60 animate-pulse" />
              </div>
              <div className="h-12 w-full rounded bg-[#1E2640]/60 animate-pulse" />
            </div>
          ))}
        </div>
      ) : items.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="p-12 text-center bg-card border border-border rounded-xl"
        >
          <div className="w-12 h-12 rounded-xl bg-success/15 border border-success/30 flex items-center justify-center text-success mx-auto mb-3">
            <UserCheck className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold text-foreground">Review Queue Cleared</h3>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
            All escalated transactions have been audited. No pending low-conviction or fraud-adjacent items remain.
          </p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <motion.div
              key={item.transaction_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="bg-card border border-border rounded-xl p-5 hover:border-warning/40 transition-colors"
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                {/* Info block */}
                <div className="space-y-2.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span className="font-mono text-xs font-semibold text-foreground bg-background px-2 py-0.5 rounded border border-border">
                      tx_{item.transaction_id}
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {item.customer_name}
                    </span>
                    <span className="text-xs font-mono font-bold text-foreground">
                      ₹{item.amount.toLocaleString('en-IN')}
                    </span>
                    <StatusBadge status={item.category || 'fraud_false_positive'} size="sm" />
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-destructive/15 text-destructive border border-destructive/30">
                      Conviction: {(item.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">Raw Failure Reason: </span>
                    <span className="font-mono italic text-foreground/80">"{item.failure_reason}"</span>
                  </div>

                  <div className="p-3 rounded-lg bg-background/70 border border-border/80 text-xs text-muted-foreground leading-relaxed">
                    <span className="text-warning font-semibold block mb-0.5 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-warning" />
                      Agent Decision Rationale:
                    </span>
                    {item.decision_reasoning}
                  </div>
                </div>

                {/* Human Approval Action Buttons */}
                <div className="flex sm:flex-row lg:flex-col gap-2 flex-shrink-0 self-end lg:self-center">
                  <button
                    onClick={() => handleApprove(item.transaction_id)}
                    className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-success hover:bg-success/90 text-success-foreground text-xs font-medium transition-colors shadow-sm cursor-pointer"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Approve Outreach
                  </button>
                  <button
                    onClick={() => handleDismiss(item.transaction_id)}
                    className="inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg border border-border bg-background hover:bg-muted text-muted-foreground hover:text-foreground text-xs font-medium transition-colors cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                    Dismiss / Suppress
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
