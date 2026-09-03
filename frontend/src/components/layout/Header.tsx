import React, { useRef, useState } from 'react';
import { Play, AlertTriangle, Radio, WifiOff, User, LogOut, ChevronDown, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLiveEvents } from '../../context/LiveEventsContext';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'text-primary bg-primary/10 border-primary/30',
  analyst: 'text-success bg-success/10 border-success/30',
  viewer: 'text-muted-foreground bg-muted/30 border-border',
};

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  const { isConnected, isRunning, runBatch, simulateFailure } = useLiveEvents();
  const { user, logout } = useAuth();
  const [failureArmed, setFailureArmed] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const handleSimulateFailure = async () => {
    setFailureArmed(true);
    await simulateFailure();
    setTimeout(() => setFailureArmed(false), 5000);
  };

  const handleLogout = async () => {
    setShowUserMenu(false);
    await logout();
  };

  const isAdmin = user?.role === 'admin';
  const isAnalystOrAbove = user?.role === 'admin' || user?.role === 'analyst';
  const roleColor = ROLE_COLORS[user?.role ?? 'viewer'] ?? ROLE_COLORS.viewer;

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
        {/* Live Status Pill */}
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

        {/* Simulate Failure — analyst+ only */}
        {isAnalystOrAbove && (
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
        )}

        {/* Run Batch — admin only */}
        {isAdmin && (
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
        )}

        {/* User pill + dropdown */}
        {user && (
          <div className="relative" ref={menuRef}>
            <button
              id="header-user-menu-btn"
              onClick={() => setShowUserMenu((v) => !v)}
              className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-full border border-border bg-card hover:bg-muted transition-colors text-xs"
            >
              <div className="w-6 h-6 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center">
                <User className="w-3 h-3 text-primary" />
              </div>
              <span className="hidden sm:block font-medium text-foreground max-w-[120px] truncate">
                {user.full_name}
              </span>
              <span className={`hidden md:inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${roleColor}`}>
                {user.role === 'admin' && <Shield className="w-2.5 h-2.5" />}
                {user.role}
              </span>
              <ChevronDown className={`w-3 h-3 text-muted-foreground transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {showUserMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 6, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 6, scale: 0.96 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 mt-2 w-56 rounded-xl border border-border bg-card shadow-xl z-50"
                >
                  {/* User info */}
                  <div className="px-4 py-3 border-b border-border">
                    <p className="text-xs font-semibold text-foreground truncate">{user.full_name}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{user.email}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      <span className="font-mono">{user.org_slug}</span>
                      {' · '}
                      <span className={`font-semibold ${roleColor.split(' ')[0]}`}>{user.role}</span>
                    </p>
                  </div>

                  {/* Logout */}
                  <div className="p-1.5">
                    <button
                      id="header-logout-btn"
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                    >
                      <LogOut className="w-3.5 h-3.5" />
                      Sign out
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}
      </div>
    </header>
  );
};
