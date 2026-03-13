'use client';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, Users, FileText, PieChart, Shield, Settings,
  Bell, Menu, X, ChevronDown, Wifi, WifiOff, RefreshCw,
  Building2, TrendingUp, ClipboardCheck, Lock, BarChart3,
  DollarSign, Globe, LogOut, Smartphone
} from 'lucide-react';
import { useAuthStore, useTenantStore, useUIStore } from '@/stores';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  roles: string[]; // empty = all roles
  badge?: number;
}

const navigation: NavItem[] = [
  { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard, roles: [] },
  { label: 'Clients', href: '/clients', icon: Users, roles: ['DATA_ENTRY','LOAN_OFFICER','BRANCH_MANAGER','CREDIT_MANAGER','CEO_CFO'] },
  { label: 'Loans', href: '/loans', icon: FileText, roles: ['LOAN_OFFICER','BRANCH_MANAGER','CREDIT_MANAGER','CEO_CFO','ACCOUNTANT'] },
  { label: 'Collections', href: '/loans?tab=collections', icon: DollarSign, roles: ['LOAN_OFFICER','BRANCH_MANAGER'] },
  { label: 'Deposits', href: '/deposits', icon: Building2, roles: ['DATA_ENTRY','LOAN_OFFICER','BRANCH_MANAGER','ACCOUNTANT','CEO_CFO'] },
  { label: 'Mobile Money', href: '/mobile-money', icon: Smartphone, roles: ['LOAN_OFFICER','BRANCH_MANAGER','ACCOUNTANT'] },
  { label: 'Reports', href: '/reports', icon: BarChart3, roles: ['BRANCH_MANAGER','CREDIT_MANAGER','ACCOUNTANT','CEO_CFO','BOARD_DIRECTOR','COMPLIANCE_OFFICER'] },
  { label: 'Compliance', href: '/compliance', icon: Shield, roles: ['COMPLIANCE_OFFICER','CEO_CFO'] },
  { label: 'Investor Portal', href: '/investors', icon: TrendingUp, roles: ['INVESTOR','CEO_CFO'] },
  { label: 'Board', href: '/board', icon: ClipboardCheck, roles: ['BOARD_DIRECTOR','CEO_CFO'] },
  { label: 'Audit Trail', href: '/audit', icon: Lock, roles: ['IT_SECURITY_ADMIN','EXTERNAL_AUDITOR','INTERNAL_AUDITOR'] },
  { label: 'Settings', href: '/settings', icon: Settings, roles: ['IT_SECURITY_ADMIN','CEO_CFO'] },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const { tenant } = useTenantStore();
  const { sidebarOpen, toggleSidebar, isOffline, pendingSyncCount, unreadCount, theme } = useUIStore();

  const userRoles = user?.roles || [];

  const visibleNav = navigation.filter(item =>
    item.roles.length === 0 || item.roles.some(r => userRoles.includes(r))
  );

  // Deposit items only visible if tenant can accept deposits
  const filteredNav = visibleNav; // TODO: filter deposit nav based on licence_tier

  return (
    <div className="flex h-screen overflow-hidden" data-theme={theme}>
      {/* Offline Banner */}
      {isOffline && (
        <div className="offline-banner">
          <WifiOff className="inline w-3 h-3 mr-1" />
          You are offline — changes will sync when connection returns
          {pendingSyncCount > 0 && ` (${pendingSyncCount} pending)`}
        </div>
      )}

      {/* Sidebar */}
      <aside className={`sidebar flex flex-col transition-all duration-300 ${
        sidebarOpen ? 'w-60' : 'w-16'
      } ${isOffline ? 'mt-7' : ''}`}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-surface-border">
          {tenant?.logo_url ? (
            <img src={tenant.logo_url} alt="" className="w-8 h-8 rounded-lg object-cover" />
          ) : (
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
                 style={{ background: `linear-gradient(135deg, var(--brand-primary), var(--brand-secondary))` }}>
              {(tenant?.trading_name || tenant?.name || 'M')[0]}
            </div>
          )}
          {sidebarOpen && (
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-content-primary truncate">
                {tenant?.trading_name || tenant?.name || 'MFI Platform'}
              </div>
              <div className="text-xs text-content-muted truncate">
                {tenant?.tagline || 'Microfinance SaaS'}
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
          {filteredNav.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href}
                    className={`sidebar-item ${isActive ? 'active' : ''}`}>
                <Icon className="w-4 h-4 shrink-0" />
                {sidebarOpen && <span className="truncate">{item.label}</span>}
                {sidebarOpen && item.badge && item.badge > 0 && (
                  <span className="ml-auto bg-status-loss text-white text-xs font-bold px-1.5 py-0.5 rounded-full">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="border-t border-surface-border p-3">
          <div className="sidebar-item">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
                 style={{ background: 'var(--brand-primary)', color: '#fff' }}>
              {user?.full_name?.[0] || '?'}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-content-primary truncate">{user?.full_name}</div>
                <div className="text-xs text-content-muted truncate">{userRoles[0] || 'User'}</div>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-surface-border bg-surface-card">
          <div className="flex items-center gap-3">
            <button onClick={toggleSidebar} className="text-content-secondary hover:text-content-primary">
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
            <h1 className="text-lg font-semibold text-content-primary">
              {visibleNav.find(n => pathname.startsWith(n.href))?.label || 'Dashboard'}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Sync indicator */}
            {pendingSyncCount > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-status-watch">
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                {pendingSyncCount} pending
              </div>
            )}
            {/* Connectivity */}
            {isOffline ? (
              <WifiOff className="w-4 h-4 text-status-watch" />
            ) : (
              <Wifi className="w-4 h-4 text-status-current" />
            )}
            {/* Notifications */}
            <button className="relative text-content-secondary hover:text-content-primary">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-status-loss text-white text-xs font-bold rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </button>
            {/* Logout */}
            <button className="text-content-secondary hover:text-content-primary">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className={`flex-1 overflow-auto p-6 ${isOffline ? 'mt-7' : ''}`}>
          {children}
        </main>
      </div>
    </div>
  );
}
