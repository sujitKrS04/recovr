import React, { useState } from 'react';
import { 
  Activity, 
  Filter, 
  Bot, 
  ShieldAlert, 
  ArrowRight,
  Radio,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import { useLiveEvents, LiveEvent } from '../context/LiveEventsContext';
import { StatusBadge } from '../components/ui/StatusBadge';
import { motion, AnimatePresence } from 'framer-motion';

function maskName(name?: string): string {
  if (!name) return 'C***r';
  return name
    .split(' ')
    .map((part) => {
      if (part.length <= 2) return part;
      return `${part[0]}***${part[part.length - 1]}`;
    })
    .join(' ');
}

export const LiveFeedPage: React.FC = () => {
  const { events, isConnected, isRunning, clearEvents } = useLiveEvents();
  const [filter, setFilter] = useState<'all' | 'classified' | 'decided' | 'executed'>('all');

  const filteredEvents = events.filter((ev) => {
    if (filter === 'classified') return ev.type === 'tx_classified';
    if (filter === 'decided') return ev.type === 'tx_decided';
    if (filter === 'executed') return ev.type === 'tx_executed' || ev.type === 'tx_failed_injected' || ev.type === 'tx_retried_recovered';
    return true;
  });

  // If no live events have occurred yet, provide initial demo stream preview
  const displayEvents: LiveEvent[] = filteredEvents.length > 0 ? filteredEvents : [
    {
      id: 'demo-1',
      type: 'tx_executed',
      transaction_id: 2,
      timestamp: '20:34:52',
      customer_name: 'Diya Sharma',
      amount: 2501,
      category: 'bank_downtime',
      action: 'instant_retry',
      status: 'recovered',
      confidence: 0.90,
      reasoning: 'Razorpay payment retry executed successfully via test gateway',
    },
    {
      id: 'demo-2',
      type: 'tx_decided',
      transaction_id: 2,
      timestamp: '20:34:52',
      customer_name: 'Diya Sharma',
      amount: 2501,
      category: 'bank_downtime',
      action: 'instant_retry',
      confidence: 0.90,
      reasoning: 'Clean signal for technical downtime (bank_downtime). Safe to auto-retry.',
    },
    {
      id: 'demo-3',
      type: 'tx_classified',
      transaction_id: 2,
      timestamp: '20:34:52',
      customer_name: 'Diya Sharma',
      amount: 2501,
      category: 'bank_downtime',
      confidence: 0.90,
      reasoning: 'Matched keyword rule: bank server undergoing scheduled maintenance',
    },
    {
      id: 'demo-4',
      type: 'tx_executed',
      transaction_id: 1,
      timestamp: '20:34:51',
      customer_name: 'Aarav Patel',
      amount: 1079,
      category: 'insufficient_funds',
      action: 'payment_link',
      status: 'recovered',
      confidence: 0.95,
      reasoning: 'Created test payment link: https://rzp.io/i/test_link_1079',
    },
    {
      id: 'demo-5',
      type: 'tx_executed',
      transaction_id: 6,
      timestamp: '20:34:50',
      customer_name: 'Rohan Gupta',
      amount: 3200,
      category: 'card_declined',
      action: 'update_card_prompt',
      status: 'suppressed',
      confidence: 0.70,
      reasoning: 'Compliance Guard blocked contact: customer is DND opted out',
    },
    {
      id: 'demo-6',
      type: 'tx_decided',
      transaction_id: 3,
      timestamp: '20:34:49',
      customer_name: 'Kavya Nair',
      amount: 4500,
      category: 'fraud_false_positive',
      action: 'escalate_human',
      confidence: 0.10,
      reasoning: 'Fraud-adjacent signal detected. High risk: auto-execution strictly prohibited.',
    },
  ];

  return (
    <div className="space-y-6 pb-12">
      {/* Feed Controller Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-card border border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center text-primary">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-foreground tracking-tight">
                Live Intervention Stream
              </h2>
              <span
                className={`flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded font-medium border ${
                  isConnected
                    ? 'bg-success/15 text-success border-success/30'
                    : 'bg-destructive/15 text-destructive border-destructive/30'
                }`}
              >
                <Radio className={`w-2.5 h-2.5 inline ${isConnected ? 'animate-pulse' : ''}`} />
                {isConnected ? (isRunning ? 'PROCESSING BATCH' : 'STREAM ACTIVE') : 'DISCONNECTED'}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Real-time WebSocket events from <code className="text-primary font-mono text-[11px]">/ws/live</code>
            </p>
          </div>
        </div>

        {/* Filter Pills & Clear */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 p-1 bg-background rounded-lg border border-border text-xs">
            <Filter className="w-3.5 h-3.5 text-muted-foreground ml-2 mr-1" />
            {(['all', 'classified', 'decided', 'executed'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={`px-2.5 py-1 rounded-md capitalize text-xs font-medium transition-all cursor-pointer ${
                  filter === type
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          {events.length > 0 && (
            <button
              onClick={clearEvents}
              title="Clear event history"
              className="p-2 rounded-lg bg-background border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Event Stream List */}
      <div className="space-y-3">
        <AnimatePresence initial={false}>
          {displayEvents.map((ev, index) => {
            const isFailureInjected = ev.type === 'tx_failed_injected';
            const isRetriedRecovered = ev.type === 'tx_retried_recovered';
            const isExecuted = ev.type === 'tx_executed' || isRetriedRecovered;
            const isDecided = ev.type === 'tx_decided';

            // Confidence styling
            const conf = ev.confidence !== undefined ? ev.confidence : 0.8;
            const confColor =
              conf >= 0.85
                ? 'bg-success/15 text-success border-success/30'
                : conf >= 0.70
                ? 'bg-primary/15 text-primary border-primary/30'
                : 'bg-warning/15 text-warning border-warning/30';

            return (
              <motion.div
                key={ev.id}
                initial={{ opacity: 0, x: -16, height: 0 }}
                animate={{ opacity: 1, x: 0, height: 'auto' }}
                exit={{ opacity: 0, x: 16, height: 0 }}
                transition={{ duration: 0.26 }}
                className={`border rounded-xl p-4.5 transition-colors relative overflow-hidden ${
                  isFailureInjected
                    ? 'bg-warning/10 border-warning/40'
                    : isRetriedRecovered
                    ? 'bg-success/10 border-success/40'
                    : 'bg-card border-border/80 hover:border-primary/40'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  {/* Left block: Icon + Tx Details + Customer + Reasoning */}
                  <div className="flex items-start gap-3">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                        isFailureInjected
                          ? 'bg-warning/20 text-warning border border-warning/40'
                          : isRetriedRecovered
                          ? 'bg-success/20 text-success border border-success/40'
                          : isExecuted
                          ? 'bg-success/15 text-success border border-success/30'
                          : isDecided
                          ? 'bg-primary/15 text-primary border border-primary/30'
                          : 'bg-muted text-muted-foreground border border-border'
                      }`}
                    >
                      {isFailureInjected ? (
                        <AlertTriangle className="w-4 h-4" />
                      ) : isRetriedRecovered ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : isExecuted ? (
                        <ArrowRight className="w-4 h-4" />
                      ) : isDecided ? (
                        <Bot className="w-4 h-4" />
                      ) : (
                        <ShieldAlert className="w-4 h-4" />
                      )}
                    </div>

                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-foreground">
                          tx_{ev.transaction_id}
                        </span>
                        <span className="text-xs text-muted-foreground font-medium">
                          · {maskName(ev.customer_name)}
                        </span>
                        {ev.amount && (
                          <span className="text-xs font-mono font-bold text-foreground">
                            (₹{Number(ev.amount).toLocaleString('en-IN')})
                          </span>
                        )}
                        <span className="text-[11px] font-mono text-muted-foreground ml-auto md:ml-0">
                          {ev.timestamp}
                        </span>
                      </div>

                      {/* AI Reasoning Text */}
                      <p className="text-xs text-muted-foreground mt-1 leading-relaxed font-sans">
                        {isFailureInjected && (
                          <span className="text-warning font-semibold mr-1.5">[DETECTED ISSUE]</span>
                        )}
                        {isRetriedRecovered && (
                          <span className="text-success font-semibold mr-1.5">[AUTOMATED RETRY & RECOVERY]</span>
                        )}
                        {ev.reasoning || (ev.error_message ? `Error: ${ev.error_message}` : 'Transaction processed through pipeline.')}
                      </p>
                    </div>
                  </div>

                  {/* Right block: Category, Action, Confidence Badge, Status */}
                  <div className="flex items-center gap-2 self-start md:self-center flex-shrink-0">
                    {ev.category && <StatusBadge status={ev.category} size="sm" />}
                    {ev.action && <StatusBadge status={ev.action} size="sm" />}
                    {ev.confidence !== undefined && (
                      <span
                        className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded border ${confColor}`}
                        title={`AI Conviction: ${(conf * 100).toFixed(0)}%`}
                      >
                        {(conf * 100).toFixed(0)}% Conviction
                      </span>
                    )}
                    {ev.status && <StatusBadge status={ev.status} size="sm" />}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
};
