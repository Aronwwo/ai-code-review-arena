import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { AuthContext } from '@/contexts/authContextBase';
import { User, LoginRequest, RegisterRequest } from '@/types';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch current user from API
  const fetchCurrentUser = useCallback(async () => {
    try {
      const response = await api.get('/auth/me');
      setUser(response.data);
      return response.data;
    } catch (error) {
      // Not authenticated - silently clear auth state
      setUser(null);
      return null;
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      await fetchCurrentUser();
      setIsLoading(false);
    };

    initAuth();
  }, [fetchCurrentUser]);

  const login = async (credentials: LoginRequest) => {
    await api.post('/auth/login', credentials);
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
