'use client';
import { useState } from 'react';
import {
  Shield, Users, Lock, AlertTriangle, Eye, Monitor, Globe,
  Clock, XCircle, Activity, Wifi, Key, RefreshCw
} from 'lucide-react';

const activeSessions = [
  { user: 'James Mensah', role: 'LOAN_OFFICER', ip: '197.251.16.42', device: 'Chrome / Android', branch: 'Accra Main', started: '08:15', lastActivity: '2 min ago', location: 'Accra, GH' },
  { user: 'Sarah Asante', role: 'BRANCH_MANAGER', ip: '197.251.22.108', device: 'Firefox / Windows', branch: 'Kumasi', started: '07:45', lastActivity: '5 min ago', location: 'Kumasi, GH' },
  { user: 'Peter Owusu', role: 'LOAN_OFFICER', ip: '41.215.180.55', device: 'Chrome / Android', branch: 'Tamale', started: '09:30', lastActivity: '1 min ago', location: 'Tamale, GH' },
  { user: 'Helen Boateng', role: 'CREDIT_MANAGER', ip: '197.251.16.42', device: 'Safari / macOS', branch: 'Head Office', started: '08:00', lastActivity: '12 min ago', location: 'Accra, GH' },
  { user: 'Dr. Kwame Mensah', role: 'BOARD_DIRECTOR', ip: '86.150.44.12', device: 'Chrome / Windows', branch: 'Remote', started: '10:15', lastActivity: '3 min ago', location: 'London, GB' },
];

const failedLogins = [
  { email: 'admin@accramfi.com', ip: '103.22.44.88', time: '10:42 AM', reason: 'WRONG_PASSWORD', attempts: 3 },
  { email: 'unknown@test.com', ip: '45.33.78.120', time: '09:15 AM', reason: 'WRONG_PASSWORD', attempts: 5 },
  { email: 'sarah.asante@accramfi.com', ip: '197.251.22.108', time: '07:30 AM', reason: 'MFA_FAILED', attempts: 1 },
];

const privilegeEvents = [
  { user: 'James Mensah', action: 'Attempted to access Board Dashboard', result: 'DENIED', time: '11:20 AM' },
  { user: 'Data Entry Clerk #2', action: 'Attempted bulk CSV export', result: 'DENIED', time: '10:05 AM' },
];

const apiKeyUsage = [
  { name: 'Accounting Integration', prefix: 'pk_live_', lastUsed: '5 min ago', calls: 234, limit: 60, status: 'ACTIVE' },
  { name: 'SMS Gateway Test', prefix: 'pk_test_', lastUsed: '2 days ago', calls: 12, limit: 60, status: 'ACTIVE' },
];

export default function SecurityDashboard() {
  const [activeTab, setActiveTab] = useState('sessions');

  const tabs = [
    { key: 'sessions', label: 'Active Sessions', icon: Monitor, badge: activeSessions.length },
    { key: 'logins', label: 'Failed Logins', icon: Lock, badge: failedLogins.length },
    { key: 'privilege', label: 'Access Violations', icon: Shield, badge: privilegeEvents.length },
    { key: 'api_keys', label: 'API Keys', icon: Key },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">Security Administration</h1>
          <p className="text-sm text-content-muted mt-1">Session management · Access monitoring · API keys</p>
        </div>
        <button className="btn-secondary text-xs"><RefreshCw className="w-3.5 h-3.5" /> Refresh</button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="kpi-card">
          <div className="kpi-label">Active Sessions</div>
          <div className="kpi-value text-status-current">{activeSessions.length}</div>
          <div className="text-xs text-content-muted mt-1 flex items-center gap-1"><Activity className="w-3 h-3" /> Live</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Failed Logins (24h)</div>
          <div className="kpi-value text-status-watch">{failedLogins.reduce((s, f) => s + f.attempts, 0)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Access Violations</div>
          <div className="kpi-value text-status-loss">{privilegeEvents.length}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Active API Keys</div>
          <div className="kpi-value">{apiKeyUsage.filter(k => k.status === 'ACTIVE').length}</div>
        </div>
      </div>

      <div className="flex gap-1 border-b border-surface-border">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                    activeTab === tab.key ? 'border-brand-primary text-content-primary' : 'border-transparent text-content-muted'
                  }`}>
            <tab.icon className="w-3.5 h-3.5" /> {tab.label}
            {tab.badge && <span className="ml-1 text-xs font-bold text-content-muted">({tab.badge})</span>}
          </button>
        ))}
      </div>

      {/* SESSIONS */}
      {activeTab === 'sessions' && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-content-muted uppercase tracking-wider bg-surface-hover">
                <th className="text-left py-2.5 px-4">User</th>
                <th className="text-left py-2.5 px-3">Role</th>
                <th className="text-left py-2.5 px-3">IP / Location</th>
                <th className="text-left py-2.5 px-3">Device</th>
                <th className="text-left py-2.5 px-3">Last Activity</th>
                <th className="text-right py-2.5 px-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {activeSessions.map((s, i) => (
                <tr key={i} className="border-t border-surface-border hover:bg-surface-hover">
                  <td className="py-2.5 px-4">
                    <div className="font-semibold text-content-primary text-xs">{s.user}</div>
                    <div className="text-xs text-content-muted">{s.branch}</div>
                  </td>
                  <td className="py-2.5 px-3"><span className="text-xs font-semibold text-content-secondary">{s.role}</span></td>
                  <td className="py-2.5 px-3">
                    <div className="text-xs font-mono text-content-secondary">{s.ip}</div>
                    <div className="text-xs text-content-muted flex items-center gap-1"><Globe className="w-3 h-3" />{s.location}</div>
                  </td>
                  <td className="py-2.5 px-3 text-xs text-content-muted">{s.device}</td>
                  <td className="py-2.5 px-3">
                    <span className="flex items-center gap-1 text-xs text-status-current"><Wifi className="w-3 h-3" />{s.lastActivity}</span>
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <button className="text-xs text-status-loss hover:text-red-300 font-semibold flex items-center gap-1 ml-auto">
                      <XCircle className="w-3 h-3" /> Kill
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* FAILED LOGINS */}
      {activeTab === 'logins' && (
        <div className="card">
          <span className="card-title">Failed login attempts — last 24 hours</span>
          <div className="space-y-3">
            {failedLogins.map((f, i) => (
              <div key={i} className="flex items-center justify-between py-3 border-b border-surface-border last:border-0">
                <div className="flex items-center gap-3">
                  <Lock className="w-4 h-4 text-status-loss" />
                  <div>
                    <div className="text-sm font-semibold text-content-primary">{f.email}</div>
                    <div className="text-xs text-content-muted">{f.ip} · {f.time}</div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="status-badge status-loss">{f.reason}</span>
                  <div className="text-xs text-content-muted mt-1">{f.attempts} attempt{f.attempts > 1 ? 's' : ''}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PRIVILEGE ESCALATIONS */}
      {activeTab === 'privilege' && (
        <div className="card">
          <span className="card-title">Access violation log</span>
          <div className="space-y-3">
            {privilegeEvents.map((e, i) => (
              <div key={i} className="flex items-center gap-3 py-3 border-b border-surface-border last:border-0">
                <Shield className="w-4 h-4 text-status-loss" />
                <div className="flex-1">
                  <div className="text-sm text-content-primary"><span className="font-semibold">{e.user}</span> — {e.action}</div>
                  <div className="text-xs text-content-muted">{e.time}</div>
                </div>
                <span className="status-badge status-loss">{e.result}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* API KEYS */}
      {activeTab === 'api_keys' && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <span className="card-title mb-0">API keys</span>
            <button className="btn-primary text-xs"><Key className="w-3 h-3" /> Create Key</button>
          </div>
          <div className="space-y-3">
            {apiKeyUsage.map((k, i) => (
              <div key={i} className="flex items-center justify-between py-3 border-b border-surface-border last:border-0">
                <div>
                  <div className="text-sm font-semibold text-content-primary">{k.name}</div>
                  <div className="text-xs text-content-muted font-mono">{k.prefix}••••••••</div>
                </div>
                <div className="flex items-center gap-4 text-xs text-content-muted">
                  <span>Last used: {k.lastUsed}</span>
                  <span>{k.calls} calls/hr</span>
                  <span className="status-badge status-current">{k.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
