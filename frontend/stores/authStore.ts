import { create } from "zustand";
import { api, User } from "@/lib/api";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.login({ email, password });
      set({ user: response.user, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Login failed",
        isLoading: false
      });
      throw error;
    }
  },

  register: async (email: string, password: string, fullName?: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.register({ email, password, full_name: fullName });
      // Auto-login after successful registration
      await api.login({ email, password });
      const user = await api.getCurrentUser();
      set({ user, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Registration failed",
        isLoading: false
      });
      throw error;
    }
  },

  logout: async () => {
    set({ isLoading: true });
    try {
      await api.logout();
      set({ user: null, isLoading: false });
    } catch (error) {
      // Even if logout fails, clear local state
      set({ user: null, isLoading: false });
    }
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const user = await api.verifyToken();
      set({ user, isLoading: false });
    } catch (error) {
      set({ user: null, isLoading: false });
    }
  },

  clearError: () => set({ error: null }),
}));
