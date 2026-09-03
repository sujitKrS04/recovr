import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { LiveEventsProvider } from './context/LiveEventsContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { AppShell } from './components/layout/AppShell';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { DashboardPage } from './pages/DashboardPage';
import { LiveFeedPage } from './pages/LiveFeedPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { ReceiptsPage } from './pages/ReceiptsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5000,
      retry: (failureCount, error: any) => {
        // Don't retry on 401 — authFetch already handles one refresh
        if (error?.status === 401) return false;
        return failureCount < 2;
      },
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <LiveEventsProvider>
          <BrowserRouter>
            <Routes>
              {/* ── Public routes ──────────────────────────────────────── */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />

              {/* ── Protected product shell ────────────────────────────── */}
              <Route
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/live" element={<LiveFeedPage />} />
                <Route
                  path="/review-queue"
                  element={
                    <ProtectedRoute requiredRole="analyst">
                      <ReviewQueuePage />
                    </ProtectedRoute>
                  }
                />
                <Route path="/receipts" element={<ReceiptsPage />} />
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </LiveEventsProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
