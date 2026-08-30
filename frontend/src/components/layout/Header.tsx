import React, { useState } from 'react';
import { Play, AlertTriangle, Radio, Wifi, WifiOff } from 'lucide-react';
import { motion } from 'framer-motion';
import { useLiveEvents } from '../../context/LiveEventsContext';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const { isConnected, isRunning, runBatch, simulateFailure } = useLiveEvents();
  const [failureArmed, setFailureArmed] = useState(false);

  const handleSimulateFailure = async () => {
    setFailureArmed(true);
    await simulateFailure();
    setTimeout(() => setFailureArmed(false), 5000);
  };

  return (
    <header className="h-16 border-b border-border/80 bg-card/60 backdrop-blur-md px-4 lg:px-8 flex items-center justify-between sticky top-0 z-20">
      {/* Title / Breadcrumb */}
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-foreground flex items-center gap-2">
          {title}
        </h1>
        {subtitle && (
          <p className="text-xs text-muted-foreground hidden sm:block">
            {subtitle}
          </p>
        )}
      </div>

      {/* Action Area */}
      <div className="flex items-center gap-3">
        {/* Live Status Pill with soft pulse */}
        <div
          className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs transition-colors ${
            isConnected
              ? 'bg-background border-border text-foreground'
              : 'bg-destructive/10 border-destructive/30 text-destructive'
          }`}
        >
          <span className="relative flex h-2 w-2">
            {isConnected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
            )}
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                isConnected ? 'bg-success' : 'bg-destructive'
              }`}
            ></span>
          </span>
          <span className="text-[11px] font-mono font-medium tracking-tight flex items-center gap-1">
            {isConnected ? (
              <>
                <Radio className="w-3 h-3 text-success inline" />
                WS LIVE
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3 text-destructive inline" />
                DISCONNECTED
              </>
            )}
          </span>
        </div>

        {/* Simulate Failure Button for live demo */}
        <button
          onClick={handleSimulateFailure}
          title="Inject artificial failure on next executor call for demo"
          className={`px-3 py-1.5 rounded-lg border text-xs font-medium transition-all duration-150 flex items-center gap-1.5 cursor-pointer ${
            failureArmed
              ? 'bg-warning/20 border-warning text-warning animate-pulse'
              : 'border-border bg-card hover:bg-muted text-muted-foreground hover:text-foreground'
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          <span className="hidden md:inline">
            {failureArmed ? 'Failure Injected' : 'Simulate Failure'}
          </span>
        </button>

        {/* Run Batch Button */}
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={() => runBatch()}
          disabled={isRunning}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-medium shadow-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          <Play
            className={`w-3.5 h-3.5 fill-current ${isRunning ? 'animate-spin' : ''}`}
          />
          <span>{isRunning ? 'Processing Batch...' : 'Run Batch'}</span>
        </motion.button>
      </div>
    </header>
  );
};
