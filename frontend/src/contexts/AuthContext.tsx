import React, { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';
import { AuthContext } from '@/contexts/authContextBase';
import { User, LoginRequest, RegisterRequest } from '@/types';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Fetch current user from API
  const fetchCurrentUser = useCallback(async (authToken: string) => {
    try {
      // Set token in header for this request
      const response = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setUser(response.data);
      localStorage.setItem('user', JSON.stringify(response.data));
      return response.data;
    } catch (error) {
      // Token invalid or expired - silently clear auth state
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setToken(null);
      setUser(null);
      return null;
    }
  }, []);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('token');

      if (storedToken) {
        setToken(storedToken);
        await fetchCurrentUser(storedToken);
      }

      setIsLoading(false);
    };

    initAuth();
  }, [fetchCurrentUser]);

  const login = async (credentials: LoginRequest) => {
    const response = await api.post('/auth/login', credentials);
    const { access_token, refresh_token } = response.data;

    // Store tokens
    localStorage.setItem('token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    setToken(access_token);

    // Fetch actual user data from API
    await fetchCurrentUser(access_token);
  };

  const register = async (data: RegisterRequest) => {
    await api.post('/auth/register', data);
    // Auto-login after registration
    await login({ email: data.email, password: data.password });
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      await fetchCurrentUser(token);
    }
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
        isAuthenticated: !!token && !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
