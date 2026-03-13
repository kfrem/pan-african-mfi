'use client';
import { useState } from 'react';
import {
  TrendingUp, TrendingDown, Users, FileText, DollarSign,
  AlertTriangle, Shield, Calendar, Download, RefreshCw,
  ArrowUpRight, ArrowDownRight, BarChart3, PieChart
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart as RePie, Pie, Cell
} from 'recharts';

// ─── Mock Data (replaced by API calls in production) ───
const kpis = [
  { label: 'Gross Portfolio', value: 'GHS 5,234,890', trend: '+12.4%', trendUp: true, icon: DollarSign },
  { label: 'Active Loans', value: '1,247', trend: '+34 this month', trendUp: true, icon: FileText },
  { label: 'PAR > 30 Days', value: '3.24%', trend: '-0.8% MoM', trendUp: false, icon: AlertTriangle },
  { label: 'Collection Rate', value: '94.8%', trend: '+2.1% MoM', trendUp: true, icon: TrendingUp },
  { label: 'Active Clients', value: '2,156', trend: '+89 this month', trendUp: true, icon: Users },
  { label: 'Capital Adequacy', value: '18.2%', trend: 'Min: 10%', trendUp: true, icon: Shield },
];

const portfolioTrend = Array.from({ length: 12 }, (_, i) => ({
  month: new Date(2025, i + 2, 1).toLocaleString('en', { month: 'short' }),
  portfolio: 3800000 + i * 180000 + Math.sin(i) * 120000,
  disbursements: 400000 + i * 20000 + Math.random() * 80000,
  collections: 350000 + i * 25000 + Math.random() * 60000,
}));

const classificationData = [
  { name: 'Current', value: 82.3, amount: 4308560, color: '#10b981' },
  { name: 'Watch', value: 8.2, amount: 429261, color: '#f59e0b' },
  { name: 'Substandard', value: 5.1, amount: 266979, color: '#f97316' },
  { name: 'Doubtful', value: 3.2, amount: 167516, color: '#ef4444' },
  { name: 'Loss', value: 1.2, amount: 62819, color: '#dc2626' },
];

const branchPerformance = [
  { branch: 'Accra Main', portfolio: 2100000, par30: 2.8, clients: 580, collection: 96.2 },
  { branch: 'Kumasi', portfolio: 1650000, par30: 3.1, clients: 420, collection: 94.5 },
  { branch: 'Tamale', portfolio: 890000, par30: 4.2, clients: 310, collection: 91.8 },
  { branch: 'Cape Coast', portfolio: 594890, par30: 3.8, clients: 246, collection: 93.1 },
];

const alerts = [
  { severity: 'CRITICAL', message: 'PAR30 approaching covenant threshold (max 5%)', time: '2h ago' },
  { severity: 'WARNING', message: 'Prudential return due in 3 days (Classification of Advances)', time: '4h ago' },
  { severity: 'WARNING', message: 'KYC expiring for 12 clients in next 30 days', time: '6h ago' },
  { severity: 'INFO', message: 'Monthly board pack auto-generated successfully', time: '1d ago' },
];

function formatCurrency(value: number): string {
  if (value >= 1000000) return `GHS ${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `GHS ${(value / 1000).toFixed(0)}K`;
  return `GHS ${value.toFixed(0)}`;
}

export default function CEODashboard() {
  const [period, setPeriod] = useState<'MTD' | 'QTD' | 'YTD'>('MTD');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">Executive Dashboard</h1>
          <p className="text-sm text-content-muted mt-1">
            Portfolio health as of {new Date().toLocaleDateString('en-GB')}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex rounded-lg overflow-hidden" style={{ border: '1px solid var(--surface-border)' }}>
            {(['MTD', 'QTD', 'YTD'] as const).map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                      className={`px-4 py-1.5 text-xs font-semibold transition-colors ${
                        period === p
                          ? 'text-white'
                          : 'text-content-muted hover:text-content-primary'
                      }`}
                      style={{ background: period === p ? 'var(--brand-primary)' : 'var(--surface-card)' }}>
                {p}
              </button>
            ))}
          </div>
          <button className="btn-primary text-xs">
            <Download className="w-3.5 h-3.5" /> Export PDF
          </button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {kpis.map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <div key={i} className="kpi-card animate-slide-up" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="flex items-center justify-between mb-2">
                <span className="kpi-label">{kpi.label}</span>
                <Icon className="w-4 h-4 text-content-muted" />
              </div>
              <div className="kpi-value text-content-primary">{kpi.value}</div>
              <div className={`kpi-trend ${kpi.trendUp ? 'text-status-current' : 'text-status-watch'}`}>
                {kpi.trendUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                {kpi.trend}
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts Row 1: Portfolio Trend + Classification */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-1">
            <span className="card-title">Portfolio trend — 12 months</span>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={portfolioTrend}>
              <defs>
                <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--brand-primary)" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="var(--brand-primary)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--content-muted)' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--content-muted)' }} axisLine={false} tickLine={false}
                     tickFormatter={(v) => `${(v/1000000).toFixed(1)}M`} />
              <Tooltip contentStyle={{ background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="portfolio" stroke="var(--brand-primary)" strokeWidth={2}
                    fill="url(#portfolioGrad)" dot={false} name="Portfolio" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Classification Donut */}
        <div className="card">
          <span className="card-title">BoG classification</span>
          <ResponsiveContainer width="100%" height={180}>
            <RePie>
              <Pie data={classificationData} cx="50%" cy="50%" innerRadius={50} outerRadius={75}
                   paddingAngle={2} dataKey="value" stroke="none">
                {classificationData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
            </RePie>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {classificationData.map(d => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: d.color }} />
                  <span className="text-content-secondary">{d.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-bold text-content-primary">{d.value}%</span>
                  <span className="text-content-muted w-20 text-right">{formatCurrency(d.amount)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Row 2: Branch Performance + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Branch Performance Table */}
        <div className="card lg:col-span-2">
          <span className="card-title">Branch performance</span>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-content-muted uppercase tracking-wider">
                  <th className="text-left py-2 pr-4">Branch</th>
                  <th className="text-right py-2 px-3">Portfolio</th>
                  <th className="text-right py-2 px-3">PAR30</th>
                  <th className="text-right py-2 px-3">Clients</th>
                  <th className="text-right py-2 pl-3">Collection %</th>
                </tr>
              </thead>
              <tbody>
                {branchPerformance.map(b => (
                  <tr key={b.branch} className="border-t border-surface-border hover:bg-surface-hover transition-colors cursor-pointer">
                    <td className="py-3 pr-4 font-semibold text-content-primary">{b.branch}</td>
                    <td className="py-3 px-3 text-right text-content-secondary">{formatCurrency(b.portfolio)}</td>
                    <td className="py-3 px-3 text-right">
                      <span className={`status-badge ${b.par30 < 3 ? 'status-current' : b.par30 < 5 ? 'status-watch' : 'status-substandard'}`}>
                        {b.par30}%
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right text-content-secondary">{b.clients.toLocaleString()}</td>
                    <td className="py-3 pl-3 text-right">
                      <span className={b.collection >= 95 ? 'text-status-current' : 'text-status-watch'}>
                        {b.collection}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Alerts Panel */}
        <div className="card">
          <span className="card-title">Active alerts</span>
          <div className="space-y-3">
            {alerts.map((alert, i) => (
              <div key={i} className="flex gap-3 p-3 rounded-lg" style={{ background: 'var(--surface-hover)' }}>
                <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                  alert.severity === 'CRITICAL' ? 'bg-status-loss animate-pulse-soft' :
                  alert.severity === 'WARNING' ? 'bg-status-watch' : 'bg-status-current'
                }`} />
                <div className="min-w-0">
                  <p className="text-xs text-content-primary leading-relaxed">{alert.message}</p>
                  <p className="text-xs text-content-muted mt-1">{alert.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
