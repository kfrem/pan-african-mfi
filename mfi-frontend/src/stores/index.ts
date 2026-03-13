import { create } from 'zustand';
import type { User, Tenant, Notification } from '@/types';

// ─── Auth Store ───
interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),
  setLoading: (isLoading) => set({ isLoading }),
  logout: () => set({ user: null, isAuthenticated: false }),
}));

// ─── Tenant Store ───
interface TenantState {
  tenant: Tenant | null;
  setTenant: (tenant: Tenant | null) => void;
  currency: string;
  setCurrency: (currency: string) => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  tenant: null,
  setTenant: (tenant) => set({ tenant, currency: tenant?.default_currency || 'GHS' }),
  currency: 'GHS',
  setCurrency: (currency) => set({ currency }),
}));

// ─── UI Store ───
interface UIState {
  sidebarOpen: boolean;
  theme: 'dark' | 'light';
  isOffline: boolean;
  pendingSyncCount: number;
  notifications: Notification[];
  unreadCount: number;
  toggleSidebar: () => void;
  setTheme: (theme: 'dark' | 'light') => void;
  setOffline: (offline: boolean) => void;
  setPendingSyncCount: (count: number) => void;
  setNotifications: (notifications: Notification[]) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  theme: 'dark',
  isOffline: false,
  pendingSyncCount: 0,
  notifications: [],
  unreadCount: 0,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setTheme: (theme) => set({ theme }),
  setOffline: (isOffline) => set({ isOffline }),
  setPendingSyncCount: (pendingSyncCount) => set({ pendingSyncCount }),
  setNotifications: (notifications) => set({
    notifications,
    unreadCount: notifications.filter(n => !n.is_read).length,
  }),
}));
