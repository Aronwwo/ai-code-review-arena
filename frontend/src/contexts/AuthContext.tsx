import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { AuthContext } from '@/contexts/authContextBase';
import { User, LoginRequest, RegisterRequest } from '@/types';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionStartTime, setSessionStartTime] = useState<number | null>(null);

  // Fetch current user from API
  const fetchCurrentUser = useCallback(async () => {
    try {
      const response = await api.get('/auth/me');
      setUser(response.data);
      // Store session start time for timer calculation
      if (!sessionStartTime) {
        setSessionStartTime(Date.now());
      }
      return response.data;
    } catch (error) {
      // Not authenticated - silently clear auth state
      setUser(null);
      setSessionStartTime(null);
      return null;
    }
  }, [sessionStartTime]);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      await fetchCurrentUser();
      setIsLoading(false);
    };

    initAuth();
  }, [fetchCurrentUser]);

  // Auto-refresh token every 35 minutes (before 45 minute expiration)
  useEffect(() => {
    if (!user) return;

    const refreshInterval = setInterval(async () => {
      try {
        await api.post('/auth/refresh');
        const now = Date.now();
        localStorage.setItem('session_start_time', now.toString());
        localStorage.setItem('last_refresh_time', now.toString());
        setSessionStartTime(now); // Reset session start time
      } catch (error) {
        console.error('Failed to auto-refresh token:', error);
      }
    }, 35 * 60 * 1000); // Every 35 minutes (10 minutes before expiration)

    return () => clearInterval(refreshInterval);
  }, [user]);

  const login = async (credentials: LoginRequest) => {
    await api.post('/auth/login', credentials);
    // Store session start time for timer
    const now = Date.now();
    localStorage.setItem('session_start_time', now.toString());
    localStorage.setItem('last_refresh_time', now.toString());
    await fetchCurrentUser();
  };

  const register = async (data: RegisterRequest) => {
    await api.post('/auth/register', data);
    // Auto-login after registration
    await login({ email: data.email, password: data.password });
  };

  const logout = async () => {
    await api.post('/auth/logout');
    setUser(null);
    setSessionStartTime(null);
    localStorage.removeItem('session_start_time');
    localStorage.removeItem('last_refresh_time');
    localStorage.removeItem('last_auto_refresh');
  };

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
