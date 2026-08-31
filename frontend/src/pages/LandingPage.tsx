import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, ArrowRight, TrendingUp, Search, Brain, Rocket } from 'lucide-react';
import { api } from '../lib/api';

// ─── Core loop steps ───────────────────────────────────────────────────────
const STEPS = [
  {
    icon: Search,
    label: 'Detect',
    desc: 'Ingest failed payment events',
    color: 'text-primary',
    border: 'border-primary/30',
    bg: 'bg-primary/10',
  },
  {
    icon: Brain,
    label: 'Classify',
    desc: 'Rules + LLM root-cause analysis',
    color: 'text-warning',
    border: 'border-warning/30',
    bg: 'bg-warning/10',
  },
  {
    icon: Zap,
    label: 'Decide',
    desc: 'Confidence-gated action routing',
    color: 'text-primary',
    border: 'border-primary/30',
    bg: 'bg-primary/10',
  },
  {
    icon: Rocket,
    label: 'Recover',
    desc: 'Automated retry, link, or escalate',
    color: 'text-success',
    border: 'border-success/30',
    bg: 'bg-success/10',
  },
];

// ─── Fade-up animation variant ─────────────────────────────────────────────
const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.45, ease: 'easeOut', delay },
});

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();

  // Live uplift number — fetched once, null means no batch run yet
  const [uplift, setUplift] = useState<number | null>(null);
  const [recoveryRate, setRecoveryRate] = useState<number | null>(null);
  const [totalRecovered, setTotalRecovered] = useState<number | null>(null);
  const [summaryLoaded, setSummaryLoaded] = useState(false);

  useEffect(() => {
    api
      .getSummary()
      .then((data) => {
        if (data.total_recovered > 0) {
          const delta = data.recovery_rate - data.baseline_recovery_rate;
          setUplift(delta);
          setRecoveryRate(data.recovery_rate);
          setTotalRecovered(data.total_recovered);
        }
        setSummaryLoaded(true);
      })
      .catch(() => setSummaryLoaded(true));
  }, []);

  const hasBatchData = summaryLoaded && uplift !== null;

  return (
    <div className="min-h-screen w-full flex flex-col bg-background overflow-y-auto overflow-x-hidden">
      {/* ── Ambient glow layer ──────────────────────────────────────────── */}
      <div
        className="pointer-events-none fixed inset-0 z-0"
        aria-hidden="true"
        style={{
          backgroundImage: `
            radial-gradient(ellipse 70% 50% at 20% 30%, rgba(99,91,255,0.08) 0%, transparent 70%),
            radial-gradient(ellipse 55% 40% at 80% 70%, rgba(0,212,160,0.05) 0%, transparent 65%)
          `,
        }}
      />

      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <header className="relative z-10 flex items-center justify-between h-14 px-6 sm:px-10 border-b border-border/50">
        {/* Wordmark */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center shadow-[0_0_12px_rgba(99,91,255,0.3)]">
            <Zap className="w-4 h-4 fill-primary text-primary" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-bold tracking-tight text-sm text-foreground font-mono">
              RECOVR
            </span>
            <span className="text-[10px] uppercase font-semibold px-1.5 rounded bg-primary/20 text-primary border border-primary/30 tracking-wider">
              AI
            </span>
          </div>
        </div>

        {/* Top-bar actions */}
        <div className="flex items-center gap-2">
          <button
            id="landing-login-btn"
            onClick={() => navigate('/dashboard')}
            className="px-4 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground border border-border/50 hover:border-border rounded-lg transition-all duration-150"
          >
            Log in
          </button>
          <button
            id="landing-signup-btn"
            onClick={() => navigate('/dashboard')}
            className="px-4 py-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-all duration-150 shadow-[0_0_12px_rgba(99,91,255,0.3)] hover:shadow-[0_0_20px_rgba(99,91,255,0.45)]"
          >
            Sign up
          </button>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 sm:px-10 py-16 sm:py-20 text-center">
        {/* Badge */}
        <motion.div {...fadeUp(0.05)} className="mb-6">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/10 text-primary text-[11px] font-semibold tracking-wider uppercase">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Razorpay AI Buildathon · Autonomous Recovery Agent
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          {...fadeUp(0.12)}
          className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground max-w-3xl leading-[1.12]"
        >
          Stop losing revenue to{' '}
          <span
            style={{
              background: 'linear-gradient(90deg, #635BFF 0%, #00D4A0 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            failed payments
          </span>
          .
        </motion.h1>

        {/* Problem statement */}
        <motion.p
          {...fadeUp(0.2)}
          className="mt-5 text-base sm:text-lg text-muted-foreground max-w-xl leading-relaxed"
        >
          Recovr intercepts every failed transaction, classifies the root cause with AI, 
          and routes it to the right recovery action automatically — so your team spends 
          time on growth, not payment retries.
        </motion.p>

        {/* Live uplift metric — only shown if a batch has run */}
        {hasBatchData && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.28 }}
            className="mt-8 flex items-center gap-5 px-6 py-4 rounded-2xl border border-success/30 bg-success/5"
          >
            <TrendingUp className="w-6 h-6 text-success flex-shrink-0" />
            <div className="text-left">
              <p className="text-xs text-muted-foreground font-medium">
                Live result from last batch run
              </p>
              <div className="flex items-baseline gap-3 mt-0.5">
                <span className="text-2xl font-bold text-success font-mono">
                  +{uplift!.toFixed(1)} pts
                </span>
                <span className="text-sm text-muted-foreground">
                  uplift vs naive baseline ·{' '}
                  <span className="text-foreground font-medium">
                    ₹{(totalRecovered! / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>{' '}
                  recovered
                </span>
              </div>
            </div>
          </motion.div>
        )}

        {/* CTA buttons */}
        <motion.div
          {...fadeUp(hasBatchData ? 0.38 : 0.3)}
          className="mt-8 sm:mt-10 flex items-center gap-3 flex-wrap justify-center"
        >
          <button
            id="landing-enter-dashboard-btn"
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground text-sm font-semibold rounded-xl hover:bg-primary/90 transition-all duration-150 shadow-[0_0_20px_rgba(99,91,255,0.35)] hover:shadow-[0_0_30px_rgba(99,91,255,0.55)] hover:-translate-y-px"
          >
            Open dashboard
            <ArrowRight className="w-4 h-4" />
          </button>
          <button
            id="landing-learn-more-btn"
            onClick={() => navigate('/live')}
            className="px-6 py-3 text-sm font-medium text-muted-foreground hover:text-foreground border border-border/50 hover:border-border rounded-xl transition-all duration-150 hover:-translate-y-px"
          >
            Watch it live
          </button>
        </motion.div>

        {/* ── 4-step core loop ──────────────────────────────────────────── */}
        <motion.div
          {...fadeUp(0.36)}
          className="mt-16 sm:mt-20 w-full max-w-3xl"
        >
          <p className="text-[11px] text-muted-foreground uppercase tracking-widest font-semibold mb-6">
            How it works
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-0">
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              return (
                <React.Fragment key={step.label}>
                  {/* Step card */}
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.38 + idx * 0.07 }}
                    className={`flex sm:flex-col items-center sm:items-center gap-3 sm:gap-2 px-5 sm:px-6 py-3 sm:py-4 rounded-xl border ${step.border} ${step.bg} min-w-[160px] sm:min-w-0 sm:flex-1 text-left sm:text-center`}
                  >
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 border ${step.border} bg-background/60`}
                    >
                      <Icon className={`w-4 h-4 ${step.color}`} />
                    </div>
                    <div>
                      <p className={`text-sm font-bold tracking-tight ${step.color}`}>
                        {step.label}
                      </p>
                      <p className="text-[11px] text-muted-foreground leading-snug mt-0.5">
                        {step.desc}
                      </p>
                    </div>
                  </motion.div>

                  {/* Arrow connector */}
                  {idx < STEPS.length - 1 && (
                    <div className="text-muted-foreground/40 sm:px-1 rotate-90 sm:rotate-0">
                      <ArrowRight className="w-4 h-4" />
                    </div>
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </motion.div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="relative z-10 flex items-center justify-center h-10 border-t border-border/30">
        <span className="text-[11px] text-muted-foreground font-mono">
          Razorpay AI Buildathon · Track 3 · Recovr
        </span>
      </footer>
    </div>
  );
};

export default LandingPage;
