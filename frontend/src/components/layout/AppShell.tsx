import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { AnimatePresence, motion } from 'framer-motion';

const routeTitles: Record<string, { title: string; subtitle: string }> = {
  '/dashboard': {
    title: 'Revenue Recovery Dashboard',
    subtitle: 'Real-time recovery metrics, root cause detection, and baseline uplift comparison',
  },
  '/live': {
    title: 'Live Action Feed',
    subtitle: 'Real-time WebSocket event stream: classification, decisioning, and automated intervention',
  },
  '/review-queue': {
    title: 'Human Review Queue',
    subtitle: 'Confidence-gated low conviction decisions and fraud-adjacent signals awaiting manual approval',
  },
  '/receipts': {
    title: 'Audit Recovery Receipts',
    subtitle: 'Transparent, immutable ledger of all interventions, automated reasoning, and recovered sums',
  },
};

export const AppShell: React.FC = () => {
  const location = useLocation();
  const currentRoute = routeTitles[location.pathname] || {
    title: 'Revenue Recovery Dashboard',
    subtitle: 'Real-time recovery metrics and pipeline state',
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          title={currentRoute.title}
          subtitle={currentRoute.subtitle}
        />

        {/* Page Content with smooth fade/slide transition */}
        <main className="flex-1 overflow-y-auto px-3 sm:px-4 lg:px-8 py-4 sm:py-6 pb-20 sm:pb-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.22, ease: 'easeOut' }}
              className="max-w-7xl mx-auto h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
};
