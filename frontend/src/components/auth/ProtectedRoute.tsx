import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** If set, the user must have this role (or higher in the hierarchy). */
  requiredRole?: 'admin' | 'analyst' | 'viewer';
}

const ROLE_RANK: Record<string, number> = {
  admin: 3,
  analyst: 2,
  viewer: 1,
};

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    // Session is being bootstrapped — show a minimal spinner
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <span className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <p className="text-xs text-muted-foreground font-mono">Restoring session…</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  if (requiredRole && user) {
    const userRank = ROLE_RANK[user.role] ?? 0;
    const requiredRank = ROLE_RANK[requiredRole] ?? 0;
    if (userRank < requiredRank) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background">
          <div className="text-center space-y-2">
            <p className="text-destructive font-semibold">Access Denied</p>
            <p className="text-xs text-muted-foreground">
              You need the <span className="font-mono">{requiredRole}</span> role to view this page.
            </p>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
};
