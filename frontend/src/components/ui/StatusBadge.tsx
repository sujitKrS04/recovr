import React from 'react';

export type StatusType = 
  | 'failed'
  | 'recovering'
  | 'recovered'
  | 'exhausted'
  | 'escalated'
  | 'suppressed'
  | 'card_declined'
  | 'insufficient_funds'
  | 'gateway_timeout'
  | 'bank_downtime'
  | 'otp_failure'
  | 'fraud_false_positive'
  | 'instant_retry'
  | 'payment_link'
  | 'update_card_prompt'
  | 'escalate_human'
  | 'suppress_dnd';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

const statusConfig: Record<string, { label: string; bg: string; text: string; border: string }> = {
  recovered: {
    label: 'Recovered',
    bg: 'bg-success/15',
    text: 'text-success',
    border: 'border-success/30',
  },
  recovering: {
    label: 'Recovering',
    bg: 'bg-primary/15',
    text: 'text-primary',
    border: 'border-primary/30',
  },
  failed: {
    label: 'Failed',
    bg: 'bg-destructive/15',
    text: 'text-destructive',
    border: 'border-destructive/30',
  },
  exhausted: {
    label: 'Exhausted',
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    border: 'border-border',
  },
  escalated: {
    label: 'Escalated',
    bg: 'bg-warning/15',
    text: 'text-warning',
    border: 'border-warning/30',
  },
  suppressed: {
    label: 'Suppressed (DND)',
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    border: 'border-border',
  },
  // Categories
  gateway_timeout: {
    label: 'Gateway Timeout',
    bg: 'bg-primary/15',
    text: 'text-primary',
    border: 'border-primary/30',
  },
  bank_downtime: {
    label: 'Bank Downtime',
    bg: 'bg-primary/15',
    text: 'text-primary',
    border: 'border-primary/30',
  },
  insufficient_funds: {
    label: 'Low Funds',
    bg: 'bg-warning/15',
    text: 'text-warning',
    border: 'border-warning/30',
  },
  card_declined: {
    label: 'Card Declined',
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    border: 'border-border',
  },
  otp_failure: {
    label: 'OTP Failure',
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    border: 'border-border',
  },
  fraud_false_positive: {
    label: 'Fraud Flag',
    bg: 'bg-warning/15',
    text: 'text-warning',
    border: 'border-warning/30',
  },
  // Actions
  instant_retry: {
    label: 'Instant Retry',
    bg: 'bg-primary/15',
    text: 'text-primary',
    border: 'border-primary/30',
  },
  payment_link: {
    label: 'Payment Link',
    bg: 'bg-success/15',
    text: 'text-success',
    border: 'border-success/30',
  },
  update_card_prompt: {
    label: 'Card Update Prompt',
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    border: 'border-border',
  },
  escalate_human: {
    label: 'Human Review',
    bg: 'bg-warning/15',
    text: 'text-warning',
    border: 'border-warning/30',
  },
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const config = statusConfig[status] || {
    label: status.replace(/_/g, ' '),
    bg: 'bg-muted',
    text: 'text-muted-foreground',
    border: 'border-border',
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center font-medium rounded-md border ${config.bg} ${config.text} ${config.border} ${sizeClasses}`}
    >
      {config.label}
    </span>
  );
};
