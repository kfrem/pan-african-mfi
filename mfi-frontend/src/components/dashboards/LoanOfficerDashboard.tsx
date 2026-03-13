'use client';
import { useState } from 'react';
import Link from 'next/link';
import {
  ClipboardList, MapPin, DollarSign, Users, Clock, CheckCircle,
  AlertTriangle, Phone, ChevronRight, Plus, Smartphone, Wifi, WifiOff
} from 'lucide-react';
import { useUIStore } from '@/stores';

// ─── Mock Data ───
const todaysTasks = [
  { id: '1', type: 'COLLECTION', client: 'Kwame Asante', loan: 'LN-202603-00012', amount: 450, dueDate: 'Today', status: 'DUE', phone: '+233 24 123 4567', location: 'Madina Market' },
  { id: '2', type: 'COLLECTION', client: 'Ama Mensah', loan: 'LN-202602-00034', amount: 280, dueDate: 'Today', status: 'DUE', phone: '+233 20 987 6543', location: 'Kaneshie' },
  { id: '3', type: 'COLLECTION', client: 'Kofi Owusu', loan: 'LN-202601-00056', amount: 620, dueDate: 'Yesterday', status: 'OVERDUE', phone: '+233 55 432 1098', location: 'Osu' },
  { id: '4', type: 'VISIT', client: 'Abena Boateng', loan: null, amount: null, dueDate: 'Today', status: 'PENDING', phone: '+233 26 765 4321', location: 'East Legon' },
  { id: '5', type: 'COLLECTION', client: 'Yaw Frimpong', loan: 'LN-202603-00078', amount: 350, dueDate: 'Tomorrow', status: 'UPCOMING', phone: '+233 54 890 1234', location: 'Tema' },
];

const myPortfolio = {
  totalLoans: 47,
  activeClients: 52,
  totalOutstanding: 234500,
  collectionsToday: 1700,
  collectionsDue: 2850,
  collectionRate: 94.2,
  overdueCount: 5,
  par30Pct: 3.8,
};

const recentRepayments = [
  { client: 'Samuel Appiah', amount: 500, method: 'CASH', time: '09:15 AM', loan: 'LN-202603-00023' },
  { client: 'Grace Addo', amount: 280, method: 'MOBILE_MONEY', time: '10:30 AM', loan: 'LN-202602-00045' },
  { client: 'Francis Mensah', amount: 750, method: 'CASH', time: '11:45 AM', loan: 'LN-202601-00067' },
];

const notifications = [
  { type: 'APPROVAL', message: 'Loan LN-202603-00089 approved by Credit Manager', time: '1h ago' },
  { type: 'OVERDUE', message: 'Kofi Owusu — 3 days overdue, escalation pending', time: '2h ago' },
  { type: 'KYC', message: 'Abena Boateng — KYC documents pending verification', time: '4h ago' },
];

function formatGHS(v: number) { return `GHS ${v.toLocaleString()}`; }

export default function LoanOfficerDashboard() {
  const { isOffline } = useUIStore();
  const [activeTab, setActiveTab] = useState<'workqueue' | 'portfolio' | 'capture'>('workqueue');

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">My Workqueue</h1>
          <p className="text-sm text-content-muted mt-1">
            {new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            {isOffline && <span className="ml-2 text-status-watch font-semibold">· Offline Mode</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/clients/new" className="btn-secondary text-xs">
            <Users className="w-3.5 h-3.5" /> New Client
          </Link>
          <Link href="/loans/new" className="btn-primary text-xs">
            <Plus className="w-3.5 h-3.5" /> New Loan
          </Link>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Collections Due Today', value: formatGHS(myPortfolio.collectionsDue), sub: `${todaysTasks.filter(t => t.status === 'DUE').length} visits`, color: 'var(--brand-primary)' },
          { label: 'Collected Today', value: formatGHS(myPortfolio.collectionsToday), sub: `${recentRepayments.length} payments`, color: '#10b981' },
          { label: 'Overdue Loans', value: String(myPortfolio.overdueCount), sub: `PAR30: ${myPortfolio.par30Pct}%`, color: '#f59e0b' },
          { label: 'My Portfolio', value: String(myPortfolio.totalLoans), sub: formatGHS(myPortfolio.totalOutstanding), color: 'var(--brand-secondary)' },
        ].map((stat, i) => (
          <div key={i} className="kpi-card">
            <div className="kpi-label">{stat.label}</div>
            <div className="kpi-value text-content-primary">{stat.value}</div>
            <div className="text-xs text-content-muted mt-1">{stat.sub}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 rounded-lg" style={{ background: 'var(--surface-card)', border: '1px solid var(--surface-border)' }}>
        {[
          { key: 'workqueue', label: 'Field Schedule', icon: MapPin },
          { key: 'capture', label: 'Capture Payment', icon: DollarSign },
          { key: 'portfolio', label: 'My Portfolio', icon: ClipboardList },
        ].map(tab => (
          <button key={tab.key}
                  onClick={() => setActiveTab(tab.key as typeof activeTab)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all flex-1 justify-center ${
                    activeTab === tab.key
                      ? 'text-white shadow-sm'
                      : 'text-content-muted hover:text-content-primary'
                  }`}
                  style={{ background: activeTab === tab.key ? 'var(--brand-primary)' : 'transparent' }}>
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'workqueue' && (
        <div className="space-y-3">
          {todaysTasks.map(task => (
            <div key={task.id} className="card flex items-center gap-4 hover:border-brand-primary transition-colors cursor-pointer">
              {/* Status indicator */}
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                task.status === 'OVERDUE' ? 'bg-status-loss/15' :
                task.status === 'DUE' ? 'bg-status-current/15' :
                task.status === 'UPCOMING' ? 'bg-blue-500/15' : 'bg-gray-500/15'
              }`}>
                {task.type === 'COLLECTION' ? (
                  <DollarSign className={`w-5 h-5 ${
                    task.status === 'OVERDUE' ? 'text-status-loss' :
                    task.status === 'DUE' ? 'text-status-current' : 'text-blue-400'
                  }`} />
                ) : (
                  <MapPin className="w-5 h-5 text-gray-400" />
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-content-primary text-sm">{task.client}</span>
                  {task.status === 'OVERDUE' && (
                    <span className="status-badge status-loss text-xs">OVERDUE</span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-0.5 text-xs text-content-muted">
                  {task.loan && <span>{task.loan}</span>}
                  <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{task.location}</span>
                </div>
              </div>

              {/* Amount */}
              {task.amount && (
                <div className="text-right shrink-0">
                  <div className="font-bold text-content-primary">{formatGHS(task.amount)}</div>
                  <div className="text-xs text-content-muted">{task.dueDate}</div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-1 shrink-0">
                <a href={`tel:${task.phone}`}
                   className="p-2 rounded-lg hover:bg-surface-hover text-content-muted">
                  <Phone className="w-4 h-4" />
                </a>
                <button className="p-2 rounded-lg hover:bg-surface-hover text-content-muted">
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'capture' && (
        <div className="card max-w-lg">
          <h3 className="text-lg font-bold text-content-primary mb-4">Capture Repayment</h3>
          <p className="text-xs text-content-muted mb-6">
            {isOffline
              ? 'You are offline. Payments will be saved locally and synced when you reconnect.'
              : 'Payment will be recorded immediately.'}
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-content-secondary uppercase tracking-wider mb-1.5">
                Client / Loan Number
              </label>
              <input type="text" placeholder="Search by name or loan number..."
                     className="w-full px-4 py-2.5 rounded-lg text-sm bg-surface-bg border border-surface-border text-content-primary" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-content-secondary uppercase tracking-wider mb-1.5">
                Amount (GHS)
              </label>
              <input type="number" placeholder="0.00"
                     className="w-full px-4 py-2.5 rounded-lg text-sm bg-surface-bg border border-surface-border text-content-primary" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-content-secondary uppercase tracking-wider mb-1.5">
                Payment Method
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { method: 'CASH', label: 'Cash', icon: DollarSign },
                  { method: 'MOBILE_MONEY', label: 'Mobile Money', icon: Smartphone },
                ].map(m => (
                  <button key={m.method}
                          className="flex items-center gap-2 px-4 py-3 rounded-lg text-xs font-semibold border border-surface-border hover:border-brand-primary transition-colors text-content-primary">
                    <m.icon className="w-4 h-4" />
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
            <button className="btn-primary w-full justify-center mt-2">
              {isOffline ? (
                <><WifiOff className="w-4 h-4" /> Save Offline</>
              ) : (
                <><CheckCircle className="w-4 h-4" /> Record Payment</>
              )}
            </button>
          </div>
        </div>
      )}

      {activeTab === 'portfolio' && (
        <div className="space-y-4">
          {/* Portfolio summary */}
          <div className="grid grid-cols-3 gap-3">
            <div className="kpi-card">
              <div className="kpi-label">Active Loans</div>
              <div className="kpi-value">{myPortfolio.totalLoans}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Outstanding</div>
              <div className="kpi-value">{formatGHS(myPortfolio.totalOutstanding)}</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-label">Collection Rate</div>
              <div className="kpi-value text-status-current">{myPortfolio.collectionRate}%</div>
            </div>
          </div>

          {/* Recent repayments */}
          <div className="card">
            <span className="card-title">Today's repayments</span>
            <div className="space-y-2">
              {recentRepayments.map((r, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-surface-border last:border-0">
                  <div>
                    <div className="text-sm font-semibold text-content-primary">{r.client}</div>
                    <div className="text-xs text-content-muted">{r.loan} · {r.method === 'MOBILE_MONEY' ? 'MoMo' : 'Cash'} · {r.time}</div>
                  </div>
                  <div className="text-sm font-bold text-status-current">{formatGHS(r.amount)}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Notifications */}
          <div className="card">
            <span className="card-title">Notifications</span>
            <div className="space-y-2">
              {notifications.map((n, i) => (
                <div key={i} className="flex items-start gap-3 py-2 border-b border-surface-border last:border-0">
                  <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                    n.type === 'OVERDUE' ? 'bg-status-loss' :
                    n.type === 'KYC' ? 'bg-status-watch' : 'bg-status-current'
                  }`} />
                  <div>
                    <div className="text-xs text-content-primary">{n.message}</div>
                    <div className="text-xs text-content-muted mt-0.5">{n.time}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
