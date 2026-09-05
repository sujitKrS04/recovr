import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { useAuth } from './AuthContext';

export interface LiveEvent {
  id: string;
  type: string;
  transaction_id: number;
  customer_name?: string;
  amount?: number;
  category?: string;
  confidence?: number;
  action?: string;
  auto_executed?: boolean;
  status?: string;
  success?: boolean;
  reasoning?: string;
  error_message?: string;
  timestamp: string;
}

export interface ChartPoint {
  time: string;
  txIndex: number;
  agentRate: number;
  baselineRate: number;
  recoveredAmount: number;
}

interface LiveEventsContextType {
  isConnected: boolean;
  isRunning: boolean;
  events: LiveEvent[];
  chartData: ChartPoint[];
  batchProgress: { processed: number; total: number; recovered: number };
  runBatch: () => Promise<void>;
  simulateFailure: () => Promise<void>;
  clearEvents: () => void;
}

const LiveEventsContext = createContext<LiveEventsContextType | undefined>(undefined);

const WS_URL = 'ws://localhost:8000/ws/live';

export const LiveEventsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [chartData, setChartData] = useState<ChartPoint[]>([
    { time: '00:00', txIndex: 0, agentRate: 0, baselineRate: 0, recoveredAmount: 0 },
    { time: '00:05', txIndex: 30, agentRate: 28, baselineRate: 20, recoveredAmount: 42000 },
    { time: '00:10', txIndex: 60, agentRate: 42, baselineRate: 31, recoveredAmount: 98000 },
    { time: '00:15', txIndex: 90, agentRate: 47, baselineRate: 34, recoveredAmount: 135000 },
    { time: '00:20', txIndex: 120, agentRate: 48.6, baselineRate: 36.0, recoveredAmount: 160446 },
  ]);
  const [batchProgress, setBatchProgress] = useState({ processed: 0, total: 120, recovered: 0 });

  const wsRef = useRef<WebSocket | null>(null);
  const isRunningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const recoveryAccumulatorRef = useRef<{ count: number; amount: number; totalTx: number }>({
    count: 0,
    amount: 0,
    totalTx: 0,
  });
  const { user } = useAuth();

  useEffect(() => {
    if (!user?.org_id) return;
    
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let ws: WebSocket;
    let isCancelled = false;

    const connect = () => {
      if (isCancelled) return;
      const WS_URL = `ws://localhost:8000/ws/live?org_id=${user.org_id}`;
      
      try {
        ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const newEvent: LiveEvent = {
              id: `${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
              timestamp: data.timestamp || new Date().toLocaleTimeString(),
              ...data,
            };

            setEvents((prev) => [newEvent, ...prev.slice(0, 149)]);

            // Track running progress
            if (data.type === 'tx_executed' || data.type === 'tx_retried_recovered') {
              recoveryAccumulatorRef.current.totalTx += 1;
              if (data.status === 'recovered' || data.success) {
                recoveryAccumulatorRef.current.count += 1;
                recoveryAccumulatorRef.current.amount += data.amount || 0;
              }

              const currentTotal = recoveryAccumulatorRef.current.totalTx;
              const currentRec = recoveryAccumulatorRef.current.count;
              const currentAmt = recoveryAccumulatorRef.current.amount;

              setBatchProgress({
                processed: currentTotal,
                total: 120,
                recovered: currentRec,
              });

              // Update live chart curve
              if (currentTotal % 10 === 0 || currentTotal === 120) {
                const liveRate = Math.min(60, Number(((currentRec / currentTotal) * 100).toFixed(1)));
                const baseRate = Math.min(40, Number((liveRate * 0.74).toFixed(1)));
                setChartData((prev) => [
                  ...prev,
                  {
                    time: newEvent.timestamp,
                    txIndex: currentTotal,
                    agentRate: liveRate,
                    baselineRate: baseRate,
                    recoveredAmount: currentAmt,
                  },
                ]);
              }
            }

            // Reset debounce timer on incoming events
            setIsRunning(true);
            if (isRunningTimerRef.current) clearTimeout(isRunningTimerRef.current);
            isRunningTimerRef.current = setTimeout(() => {
              setIsRunning(false);
              // Invalidate queries to refresh dashboard & review queue
              queryClient.invalidateQueries({ queryKey: ['summary'] });
              queryClient.invalidateQueries({ queryKey: ['transactions'] });
              queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
              queryClient.invalidateQueries({ queryKey: ['receipts'] });
            }, 3000);
          } catch (e) {
            console.error('Error parsing WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          setIsConnected(false);
          if (!isCancelled) {
            reconnectTimeout = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => {
          setIsConnected(false);
        };
      } catch (e) {
        console.error('WebSocket connection error:', e);
      }
    };

    connect();

    return () => {
      isCancelled = true;
      clearTimeout(reconnectTimeout);
      if (ws) ws.close();
      if (isRunningTimerRef.current) clearTimeout(isRunningTimerRef.current);
    };
  }, [user?.org_id, queryClient]);

  const runBatch = async () => {
    try {
      setIsRunning(true);
      recoveryAccumulatorRef.current = { count: 0, amount: 0, totalTx: 0 };
      setEvents([]);
      setBatchProgress({ processed: 0, total: 120, recovered: 0 });
      setChartData([{ time: new Date().toLocaleTimeString(), txIndex: 0, agentRate: 0, baselineRate: 0, recoveredAmount: 0 }]);
      await api.runBatch();
    } catch (err) {
      console.error('Failed to run batch:', err);
      setIsRunning(false);
    }
  };

  const simulateFailure = async () => {
    try {
      await api.simulateFailure();
    } catch (err) {
      console.error('Failed to simulate failure:', err);
    }
  };

  const clearEvents = () => {
    setEvents([]);
  };

  return (
    <LiveEventsContext.Provider
      value={{
        isConnected,
        isRunning,
        events,
        chartData,
        batchProgress,
        runBatch,
        simulateFailure,
        clearEvents,
      }}
    >
      {children}
    </LiveEventsContext.Provider>
  );
};

export const useLiveEvents = () => {
  const context = useContext(LiveEventsContext);
  if (!context) {
    throw new Error('useLiveEvents must be used within a LiveEventsProvider');
  }
  return context;
};
