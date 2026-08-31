import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Activity, 
  ShieldAlert, 
  Receipt, 
  Bot,
  Zap,
  CheckCircle2
} from 'lucide-react';

interface SidebarProps {
  onRunBatch?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const navItems = [
    {
      name: 'Dashboard',
      path: '/dashboard',
      icon: LayoutDashboard,
    },
    {
      name: 'Live Feed',
      path: '/live',
      icon: Activity,
      badge: 'LIVE',
    },
    {
      name: 'Review Queue',
      path: '/review-queue',
      icon: ShieldAlert,
      badge: '4',
    },
    {
      name: 'Receipts',
      path: '/receipts',
      icon: Receipt,
    },
  ];

  return (
    <>
      {/* Desktop & Tablet Sidebar (sm and up) */}
      <aside className="hidden sm:flex w-16 md:w-20 lg:w-64 bg-card border-r border-border flex-col justify-between flex-shrink-0 transition-all duration-300 z-30 select-none">
        {/* Brand Header */}
        <div>
          <div className="h-16 flex items-center px-3.5 md:px-4 lg:px-6 border-b border-border/70 gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary/20 border border-primary/40 flex items-center justify-center text-primary flex-shrink-0 shadow-glow-primary">
              <Zap className="w-5 h-5 fill-primary text-primary" />
            </div>
            <div className="hidden lg:flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-bold tracking-tight text-base text-foreground font-mono">
                  RECOVR
                </span>
                <span className="text-[10px] uppercase font-semibold px-1.5 py-0.2 rounded bg-primary/20 text-primary border border-primary/30 tracking-wider">
                  AI
                </span>
              </div>
              <span className="text-[11px] text-muted-foreground tracking-tight">
                Autonomous Recovery Agent
              </span>
            </div>
          </div>

          {/* Navigation links */}
          <nav className="p-2 md:p-3 lg:p-4 space-y-1.5">
            <div className="hidden lg:block px-2 pb-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
              Navigation
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center justify-center lg:justify-start gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 group relative ${
                      isActive
                        ? 'bg-primary text-primary-foreground shadow-sm'
                        : 'text-muted-foreground hover:text-foreground hover:bg-background/60'
                    }`
                  }
                  title={item.name}
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        className={`w-4 h-4 flex-shrink-0 ${
                          isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-foreground'
                        }`}
                      />
                      <span className="hidden lg:inline tracking-tight font-medium">
                        {item.name}
                      </span>
                      {item.badge && (
                        <span
                          className={`hidden lg:inline-flex items-center ml-auto px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                            isActive
                              ? 'bg-white/20 text-white'
                              : item.badge === 'LIVE'
                              ? 'bg-success/20 text-success border border-success/30'
                              : 'bg-warning/20 text-warning border border-warning/30'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Footer / System status info */}
        <div className="p-3 lg:p-4 border-t border-border/70">
          <div className="hidden lg:flex flex-col gap-2 p-3 rounded-lg bg-background/60 border border-border text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Bot className="w-3.5 h-3.5 text-primary" />
                Engine
              </span>
              <span className="text-foreground font-mono font-medium">
                Rules + LLM
              </span>
            </div>
            <div className="flex items-center justify-between pt-1 border-t border-border/50">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                Guard
              </span>
              <span className="text-success font-medium">
                Enforced
              </span>
            </div>
          </div>

          <div className="mt-2 text-center hidden lg:block">
            <span className="text-[10px] text-muted-foreground font-mono">
              Razorpay AI Buildathon · Track 3
            </span>
          </div>
        </div>
      </aside>

      {/* Mobile Bottom Navigation Bar (below sm / <640px) */}
      <nav className="sm:hidden fixed bottom-0 left-0 right-0 h-14 bg-card/95 backdrop-blur-md border-t border-border flex items-center justify-around z-40 px-2 select-none">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center p-1.5 rounded-lg text-[10px] font-medium transition-all ${
                  isActive ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
                }`
              }
            >
              <Icon className="w-4 h-4 mb-0.5" />
              <span>{item.name.replace(' Queue', '')}</span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
};
