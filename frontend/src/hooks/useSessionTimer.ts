import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/useAuth';

interface SessionTimer {
  timeRemaining: number; // seconds until expiration
  minutesRemaining: number;
  secondsRemaining: number;
  isExpiringSoon: boolean; // true if less than 5 minutes remaining
  formattedTime: string; // "MM:SS" format
  refreshSession: () => Promise<void>;
}

const ACCESS_TOKEN_EXPIRE_MINUTES = 45; // Match backend setting
const WARNING_THRESHOLD_MINUTES = 5; // Show warning when less than 5 minutes left


/**
 * Hook to track session expiration time and provide countdown timer.
 * Automatically refreshes token when needed.
 */
export function useSessionTimer(): SessionTimer {
  const { isAuthenticated, user } = useAuth();
  const [timeRemaining, setTimeRemaining] = useState<number>(ACCESS_TOKEN_EXPIRE_MINUTES * 60);
  const sessionStartTimeRef = useRef<number | null>(null);
  const [lastRefreshTime, setLastRefreshTime] = useState<number | null>(null);

  // Initialize session start time when user logs in
  useEffect(() => {
    if (isAuthenticated && user) {
      const stored = localStorage.getItem('session_start_time');
      if (!stored) {
        const now = Date.now();
        localStorage.setItem('session_start_time', now.toString());
        sessionStartTimeRef.current = now;
        setLastRefreshTime(now);
      } else {
        sessionStartTimeRef.current = parseInt(stored, 10);
        const refreshTime = localStorage.getItem('last_refresh_time');
        setLastRefreshTime(refreshTime ? parseInt(refreshTime, 10) : parseInt(stored, 10));
      }
    } else {
      localStorage.removeItem('session_start_time');
      localStorage.removeItem('last_refresh_time');
      sessionStartTimeRef.current = null;
      setLastRefreshTime(null);
    }
  }, [isAuthenticated, user]);

  // Refresh session token
  const refreshSession = useCallback(async () => {
    try {
      const api = (await import('@/lib/api')).default;
      await api.post('/auth/refresh');
      const now = Date.now();
      setLastRefreshTime(now);
      localStorage.setItem('last_refresh_time', now.toString());
      // Reset session start time to now (new 45 minute session)
      if (sessionStartTimeRef.current) {
        sessionStartTimeRef.current = now;
        localStorage.setItem('session_start_time', now.toString());
      }
    } catch (error) {
      console.error('Failed to refresh session:', error);
    }
  }, []);

  // Update countdown timer
  useEffect(() => {
    if (!isAuthenticated || !lastRefreshTime) {
      setTimeRemaining(0);
      return;
    }

    const updateTimer = () => {
      const now = Date.now();
      const expirationTime = lastRefreshTime + (ACCESS_TOKEN_EXPIRE_MINUTES * 60 * 1000);
      const remaining = Math.max(0, Math.floor((expirationTime - now) / 1000));
      setTimeRemaining(remaining);

      // Auto-refresh when less than 5 minutes remaining (only once per minute to avoid spam)
      if (remaining > 0 && remaining < WARNING_THRESHOLD_MINUTES * 60 && remaining % 60 === 0) {
        const lastAutoRefresh = localStorage.getItem('last_auto_refresh');
        const nowMs = Date.now();
        if (!lastAutoRefresh || nowMs - parseInt(lastAutoRefresh, 10) > 60000) {
          localStorage.setItem('last_auto_refresh', nowMs.toString());
          refreshSession();
        }
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000); // Update every second

    return () => clearInterval(interval);
  }, [isAuthenticated, lastRefreshTime, refreshSession]);

  const minutesRemaining = Math.floor(timeRemaining / 60);
  const secondsRemaining = timeRemaining % 60;
  const isExpiringSoon = timeRemaining > 0 && timeRemaining < WARNING_THRESHOLD_MINUTES * 60;
  const formattedTime = `${String(minutesRemaining).padStart(2, '0')}:${String(secondsRemaining).padStart(2, '0')}`;

  return {
    timeRemaining,
    minutesRemaining,
    secondsRemaining,
    isExpiringSoon,
    formattedTime,
    refreshSession,
  };
}
