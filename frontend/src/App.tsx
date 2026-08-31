import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LiveEventsProvider } from './context/LiveEventsContext';
import { AppShell } from './components/layout/AppShell';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { LiveFeedPage } from './pages/LiveFeedPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { ReceiptsPage } from './pages/ReceiptsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5000,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <LiveEventsProvider>
        <BrowserRouter>
          <Routes>
            {/* Landing page — outside the AppShell, no sidebar/header */}
            <Route path="/" element={<LandingPage />} />

            {/* Product shell — all inner routes share the AppShell layout */}
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/live" element={<LiveFeedPage />} />
              <Route path="/review-queue" element={<ReviewQueuePage />} />
              <Route path="/receipts" element={<ReceiptsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </LiveEventsProvider>
    </QueryClientProvider>
  );
}

export default App;
