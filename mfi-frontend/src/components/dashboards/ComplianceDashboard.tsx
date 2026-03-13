'use client';
import { useState } from 'react';
import {
  Shield, AlertTriangle, FileText, Calendar, Users, Clock,
  CheckCircle, XCircle, Send, Eye, ChevronRight, Filter
} from 'lucide-react';

// ─── Mock Data ───
const kycOverview = {
  total_clients: 2156,
  verified: 1842,
  complete: 189,
  incomplete: 98,
  expired: 27,
  pct_verified: 85.4,
};

const amlAlerts = [
  { id: '1', client: 'Kwame Asante Enterprises', type: 'LARGE_CASH', amount: 85000, currency: 'GHS', status: 'OPEN', risk: 75, age: '2h', description: 'Cash deposit exceeding CTR threshold (GHS 50,000)' },
  { id: '2', client: 'Abena Osei', type: 'UNUSUAL_PATTERN', amount: 45000, currency: 'GHS', status: 'UNDER_REVIEW', risk: 60, age: '1d', description: 'Full loan repayment significantly earlier than scheduled' },
  { id: '3', client: 'Group 7 — Madina Market', type: 'STRUCTURING', amount: 48000, currency: 'GHS', status: 'ESCALATED', risk: 85, age: '3d', description: '4 cash transactions of GHS 48,000 each within 7 days' },
  { id: '4', client: 'Francis Trading Co', type: 'LARGE_CASH', amount: 92000, currency: 'GHS', status: 'OPEN', risk: 65, age: '5h', description: 'Cash withdrawal exceeding CTR threshold' },
  { id: '5', client: 'Yaw Frimpong', type: 'PEP_TRANSACTION', amount: 15000, currency: 'GHS', status: 'OPEN', risk: 70, age: '8h', description: 'Transaction by Politically Exposed Person' },
];

const strs = [
  { id: 'STR-2026-001', client: 'Group 7 — Madina Market', type: 'STR', status: 'SUBMITTED', fic_ref: 'FIC-2026-00456', submitted: '2026-03-10' },
  { id: 'STR-2026-002', client: 'Unknown Depositor', type: 'STR', status: 'DRAFT', fic_ref: '', submitted: '' },
  { id: 'CTR-2026-015', client: 'Kwame Asante Enterprises', type: 'CTR', status: 'SUBMITTED', fic_ref: 'FIC-2026-00789', submitted: '2026-03-12' },
];

const regulatoryCalendar = [
  { name: 'Classification of Advances', frequency: 'Monthly', due: '2026-03-15', status: 'PENDING', daysLeft: 2 },
  { name: 'Capital Adequacy Return', frequency: 'Monthly', due: '2026-03-15', status: 'PENDING', daysLeft: 2 },
  { name: 'Liquidity Return', frequency: 'Monthly', due: '2026-03-15', status: 'PENDING', daysLeft: 2 },
  { name: 'AML/CFT Compliance Summary', frequency: 'Quarterly', due: '2026-03-31', status: 'PENDING', daysLeft: 18 },
  { name: 'Statement of Assets & Liabilities', frequency: 'Monthly', due: '2026-02-15', status: 'SUBMITTED', daysLeft: 0 },
  { name: 'Classification of Advances', frequency: 'Monthly', due: '2026-02-15', status: 'OVERDUE', daysLeft: -26 },
];

const alertStatusColors: Record<string, string> = {
  OPEN: 'status-loss', UNDER_REVIEW: 'status-watch', ESCALATED: 'bg-purple-500/15 text-purple-400',
  STR_FILED: 'status-current', CLOSED_NO_ACTION: 'bg-gray-500/15 text-gray-400',
};
const returnStatusColors: Record<string, string> = {
  PENDING: 'status-watch', SUBMITTED: 'status-current', OVERDUE: 'status-loss', GENERATED: 'bg-blue-500/15 text-blue-400',
};

export default function ComplianceDashboard() {
  const [activeTab, setActiveTab] = useState('alerts');
  const [alertFilter, setAlertFilter] = useState('');

  const filteredAlerts = alertFilter
    ? amlAlerts.filter(a => a.status === alertFilter)
    : amlAlerts;

  const tabs = [
    { key: 'alerts', label: 'AML Alerts', icon: AlertTriangle, badge: amlAlerts.filter(a => a.status === 'OPEN').length },
    { key: 'strs', label: 'STR / CTR', icon: Send, badge: strs.filter(s => s.status === 'DRAFT').length },
    { key: 'kyc', label: 'KYC Status', icon: Users },
    { key: 'calendar', label: 'Regulatory Calendar', icon: Calendar, badge: regulatoryCalendar.filter(r => r.status === 'OVERDUE').length },
  ];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">Compliance Dashboard</h1>
          <p className="text-sm text-content-muted mt-1">AML/CFT monitoring · KYC oversight · Regulatory returns</p>
        </div>
      </div>

      {/* KYC Summary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="kpi-card">
          <div className="kpi-label">KYC Verified</div>
          <div className="kpi-value text-status-current">{kycOverview.pct_verified}%</div>
          <div className="text-xs text-content-muted mt-1">{kycOverview.verified} / {kycOverview.total_clients}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Incomplete KYC</div>
          <div className="kpi-value text-status-watch">{kycOverview.incomplete}</div>
          <div className="text-xs text-content-muted mt-1">Require action</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Expired Docs</div>
          <div className="kpi-value text-status-loss">{kycOverview.expired}</div>
          <div className="text-xs text-content-muted mt-1">Need renewal</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Open AML Alerts</div>
          <div className="kpi-value text-status-loss">{amlAlerts.filter(a => a.status === 'OPEN').length}</div>
          <div className="text-xs text-content-muted mt-1">Require review</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Overdue Returns</div>
          <div className="kpi-value text-status-loss">{regulatoryCalendar.filter(r => r.status === 'OVERDUE').length}</div>
          <div className="text-xs text-content-muted mt-1">Past deadline</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-surface-border">
        {tabs.map(tab => (
          <button key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                    activeTab === tab.key
                      ? 'border-brand-primary text-content-primary'
                      : 'border-transparent text-content-muted hover:text-content-secondary'
                  }`}>
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
            {tab.badge && tab.badge > 0 && (
              <span className="ml-1 w-5 h-5 bg-status-loss text-white text-xs font-bold rounded-full flex items-center justify-center">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* AML ALERTS TAB */}
      {activeTab === 'alerts' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-2">
            <Filter className="w-4 h-4 text-content-muted" />
            {['', 'OPEN', 'UNDER_REVIEW', 'ESCALATED'].map(f => (
              <button key={f} onClick={() => setAlertFilter(f)}
                      className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                        alertFilter === f
                          ? 'text-white'
                          : 'text-content-muted hover:text-content-primary'
                      }`}
                      style={{ background: alertFilter === f ? 'var(--brand-primary)' : 'var(--surface-card)', border: '1px solid var(--surface-border)' }}>
                {f || 'All'}
              </button>
            ))}
          </div>

          {filteredAlerts.map(alert => (
            <div key={alert.id} className="card flex items-start gap-4 hover:border-brand-primary transition-colors cursor-pointer">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
                alert.risk >= 80 ? 'bg-status-loss/15' : alert.risk >= 60 ? 'bg-status-watch/15' : 'bg-blue-500/15'
              }`}>
                <AlertTriangle className={`w-5 h-5 ${
                  alert.risk >= 80 ? 'text-status-loss' : alert.risk >= 60 ? 'text-status-watch' : 'text-blue-400'
                }`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-content-primary text-sm">{alert.client}</span>
                  <span className={`status-badge ${alertStatusColors[alert.status]}`}>{alert.status}</span>
                  <span className="text-xs text-content-muted px-2 py-0.5 rounded-full" style={{ background: 'var(--surface-hover)' }}>
                    Risk: {alert.risk}
                  </span>
                </div>
                <p className="text-xs text-content-secondary">{alert.description}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-content-muted">
                  <span>{alert.type}</span>
                  <span>{alert.currency} {alert.amount.toLocaleString()}</span>
                  <span>{alert.age} ago</span>
                </div>
              </div>
              <ChevronRight className="w-4 h-4 text-content-muted shrink-0 mt-2" />
            </div>
          ))}
        </div>
      )}

      {/* STR TAB */}
      {activeTab === 'strs' && (
        <div className="card">
          <span className="card-title">Suspicious & Cash Transaction Reports</span>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-content-muted uppercase tracking-wider">
                <th className="text-left py-2">Report ID</th>
                <th className="text-left py-2">Client</th>
                <th className="text-center py-2">Type</th>
                <th className="text-center py-2">Status</th>
                <th className="text-left py-2">FIC Reference</th>
                <th className="text-left py-2">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {strs.map(s => (
                <tr key={s.id} className="border-t border-surface-border hover:bg-surface-hover cursor-pointer">
                  <td className="py-3 font-mono text-xs font-semibold">{s.id}</td>
                  <td className="py-3 text-content-primary">{s.client}</td>
                  <td className="py-3 text-center">
                    <span className={`status-badge ${s.type === 'STR' ? 'status-loss' : 'status-watch'}`}>{s.type}</span>
                  </td>
                  <td className="py-3 text-center">
                    <span className={`status-badge ${returnStatusColors[s.status]}`}>{s.status}</span>
                  </td>
                  <td className="py-3 text-xs text-content-muted font-mono">{s.fic_ref || '—'}</td>
                  <td className="py-3 text-xs text-content-muted">{s.submitted || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* REGULATORY CALENDAR TAB */}
      {activeTab === 'calendar' && (
        <div className="card">
          <span className="card-title">Regulatory return calendar</span>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-content-muted uppercase tracking-wider">
                <th className="text-left py-2">Return</th>
                <th className="text-center py-2">Frequency</th>
                <th className="text-left py-2">Due Date</th>
                <th className="text-center py-2">Status</th>
                <th className="text-right py-2">Days</th>
              </tr>
            </thead>
            <tbody>
              {regulatoryCalendar.map((r, i) => (
                <tr key={i} className="border-t border-surface-border">
                  <td className="py-3 font-semibold text-content-primary">{r.name}</td>
                  <td className="py-3 text-center text-xs text-content-muted">{r.frequency}</td>
                  <td className="py-3 text-xs text-content-secondary">{r.due}</td>
                  <td className="py-3 text-center">
                    <span className={`status-badge ${returnStatusColors[r.status]}`}>{r.status}</span>
                  </td>
                  <td className={`py-3 text-right text-xs font-bold ${
                    r.daysLeft < 0 ? 'text-status-loss' : r.daysLeft <= 3 ? 'text-status-watch' : 'text-content-muted'
                  }`}>
                    {r.daysLeft < 0 ? `${Math.abs(r.daysLeft)}d overdue` : r.daysLeft === 0 ? 'Done' : `${r.daysLeft}d left`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* KYC TAB */}
      {activeTab === 'kyc' && (
        <div className="space-y-4">
          <div className="card">
            <span className="card-title">KYC completeness breakdown</span>
            <div className="space-y-3">
              {[
                { label: 'Verified', count: kycOverview.verified, pct: (kycOverview.verified / kycOverview.total_clients * 100), color: '#10b981' },
                { label: 'Complete (unverified)', count: kycOverview.complete, pct: (kycOverview.complete / kycOverview.total_clients * 100), color: '#3b82f6' },
                { label: 'Incomplete', count: kycOverview.incomplete, pct: (kycOverview.incomplete / kycOverview.total_clients * 100), color: '#f59e0b' },
                { label: 'Expired', count: kycOverview.expired, pct: (kycOverview.expired / kycOverview.total_clients * 100), color: '#ef4444' },
              ].map(row => (
                <div key={row.label}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="flex items-center gap-2 text-content-secondary">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ background: row.color }} />
                      {row.label}
                    </span>
                    <span className="font-bold text-content-primary">{row.count} ({row.pct.toFixed(1)}%)</span>
                  </div>
                  <div className="h-2 rounded-full" style={{ background: 'var(--surface-bg)' }}>
                    <div className="h-full rounded-full transition-all duration-1000"
                         style={{ width: `${row.pct}%`, background: row.color }} />
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
