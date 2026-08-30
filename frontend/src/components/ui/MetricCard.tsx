import React from 'react';
import { LucideIcon } from 'lucide-react';
import { CountUp } from './CountUp';
import { motion } from 'framer-motion';

interface MetricCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  subtitle?: string;
  icon: LucideIcon;
  badge?: {
    text: string;
    variant: 'success' | 'warning' | 'primary' | 'muted';
  };
  delay?: number;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  subtitle,
  icon: Icon,
  badge,
  delay = 0,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
      className="bg-card border border-border rounded-xl p-5 relative overflow-hidden flex flex-col justify-between hover:border-primary/40 transition-colors duration-200"
    >
      {/* Top row */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {title}
        </span>
        <div className="w-8 h-8 rounded-lg bg-background/80 border border-border flex items-center justify-center text-primary">
          <Icon className="w-4 h-4" />
        </div>
      </div>

      {/* Metric value */}
      <div className="mb-2">
        <div className="text-2xl lg:text-3xl font-semibold tracking-tight text-foreground font-mono">
          <CountUp
            value={value}
            prefix={prefix}
            suffix={suffix}
            decimals={decimals}
          />
        </div>
      </div>

      {/* Bottom row / Subtitle & Badge */}
      <div className="flex items-center justify-between text-xs pt-2 border-t border-border/50 text-muted-foreground">
        <span>{subtitle || 'Updated just now'}</span>
        {badge && (
          <span
            className={`px-2 py-0.5 rounded-md text-[11px] font-medium ${
              badge.variant === 'success'
                ? 'bg-success/15 text-success border border-success/30'
                : badge.variant === 'warning'
                ? 'bg-warning/15 text-warning border border-warning/30'
                : badge.variant === 'primary'
                ? 'bg-primary/15 text-primary border border-primary/30'
                : 'bg-muted text-muted-foreground border border-border'
            }`}
          >
            {badge.text}
          </span>
        )}
      </div>
    </motion.div>
  );
};
