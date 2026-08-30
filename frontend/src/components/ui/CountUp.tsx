import React, { useEffect } from 'react';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';

interface CountUpProps {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  duration?: number;
  className?: string;
}

export const CountUp: React.FC<CountUpProps> = ({
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  duration = 1.4,
  className = '',
}) => {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => {
    const formatted = decimals > 0 
      ? latest.toFixed(decimals) 
      : Math.round(latest).toLocaleString('en-IN');
    return `${prefix}${formatted}${suffix}`;
  });

  useEffect(() => {
    const controls = animate(count, value, {
      duration,
      ease: [0.16, 1, 0.3, 1], // smooth cubic-bezier easeOutExpo
    });
    return controls.stop;
  }, [value, duration]);

  return <motion.span className={className}>{rounded}</motion.span>;
};
