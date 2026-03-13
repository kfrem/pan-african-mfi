'use client';
import { useState } from 'react';
import {
  Shield, AlertTriangle, Users, TrendingUp, FileText, Download,
  CheckCircle, XCircle, Clock, BarChart3, PieChart, Lock
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadialBarChart, RadialBar, Legend
} from 'recharts';

// ─── Mock Data ───
const governanceKPIs = [
  { label: 'Capital Adequacy', value: 18.2, min: 10, status: 'pass', unit: '%' },
  { label: 'Liquidity Ratio', value: 22.0, min: 15, status: 'pass', unit: '%' },
  { label: 'PAR > 30', value: 3.24, max: 5, status: 'pass', unit: '%' },
  { label: 'NPL Ratio', value: 4.1, max: 8, status: 'pass', unit: '%' },
];

const insiderLoans = [
  { name: 'John Mensah (Director)', relationship: 'Board Director', outstanding: 125000, limit: 250000, status: 'WITHIN_LIMIT' },
  { name: 'Sarah Owusu (CFO)', relationship: 'Senior Management', outstanding: 85000, limit: 150000, status: 'WITHIN_LIMIT' },
  { name: 'Peter Asante (Board Chair spouse)', relationship: 'Related Party', outstanding: 180000, limit: 200000, status: 'APPROACHING' },
];

const largeExposures = [
  { borrower: 'Asante Farms Ltd', outstanding: 480000, pctCapital: 7.2, classification: 'CURRENT' },
  { borrower: 'Mensah Trading Co', outstanding: 350000, pctCapital: 5.3, classification: 'CURRENT' },
  { borrower: 'Golden Star Enterprises', outstanding: 290000, pctCapital: 4.4, classification: 'WATCH' },
  { borrower: 'Owusu Construction', outstanding: 250000, pctCapital: 3.8, classification: 'CURRENT' },
  { borrower: 'Accra Fresh Foods', outstanding: 220000, pctCapital: 3.3, classification: 'CURRENT' },
];

const auditFindings = [
  { finding: 'KYC documentation gaps in Branch B', severity: 'MEDIUM', status: 'OPEN', age: '15 days' },
  { finding: 'Segregation of duties violation — loan officer self-approved', severity: 'HIGH', status: 'UNDER_REVIEW', age: '8 days' },
  { finding: 'Late prudential return submission — Q4 2025', severity: 'LOW', status: 'RESOLVED', age: '45 days' },
];

const riskRegister = [
  { risk: 'Credit concentration in agriculture sector', likelihood: 'MEDIUM', impact: 'HIGH', owner: 'Credit Manager', status: 'MONITORED' },
  { risk: 'Mobile money reconciliation delays', likelihood: 'LOW', impact: 'MEDIUM', owner: 'Finance Officer', status: 'MITIGATED' },
  { risk: 'Staff turnover in rural branches', likelihood: 'HIGH', impact: 'MEDIUM', owner: 'HR Manager', status: 'ACTIVE' },
  { risk: 'Regulatory change — BoG new capital requirements', likelihood: 'MEDIUM', impact: 'HIGH', owner: 'CEO', status: 'MONITORED' },
];

function formatGHS(v: number) { return `GHS ${v.toLocaleString()}`; }

export default function BoardDashboard() {
  const [period, setPeriod] = useState<'WEEKLY' | 'MONTHLY' | 'QUARTERLY'>('MONTHLY');
  const [activeTab, setActiveTab] = useState('overview');

  const tabs = [
    { key: 'overview', label: 'Overview', icon: BarChart3 },
    { key: 'governance', label: 'Governance', icon: Shield },
    { key: 'risk', label: 'Risk Register', icon: AlertTriangle },
    { key: 'insiders', label: 'Insider Lending', icon: Users },
    { key: 'board_pack', label: 'Board Pack', icon: FileText },
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">Board Dashboard</h1>
          <p className="text-sm text-content-muted mt-1">
            Governance oversight · {new Date().toLocaleDateString('en-GB', { month: 'long', year: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg overflow-hidden" style={{ border: '1px solid var(--surface-border)' }}>
            {(['WEEKLY', 'MONTHLY', 'QUARTERLY'] as const).map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                      className={`px-3 py-1.5 text-xs font-semibold ${
                        period === p ? 'text-white' : 'text-content-muted'
                      }`}
                      style={{ background: period === p ? 'var(--brand-primary)' : 'var(--surface-card)' }}>
                {p}
              </button>
            ))}
          </div>
          <button className="btn-primary text-xs">
            <Download className="w-3.5 h-3.5" /> Generate Board Pack
          </button>
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
          </button>
        ))}
      </div>

      {/* OVERVIEW TAB */}
      {activeTab === 'overview' && (
        <div className="space-y-5">
          {/* Governance KPIs with gauges */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {governanceKPIs.map((kpi, i) => {
              const limit = kpi.min || kpi.max || 0;
              const pct = kpi.min
                ? Math.min((kpi.value / (limit * 2)) * 100, 100)
                : Math.min((kpi.value / (limit * 1.5)) * 100, 100);
              const isGood = kpi.min ? kpi.value >= kpi.min : kpi.value <= (kpi.max || 0);

              return (
                <div key={i} className="kpi-card">
                  <div className="flex items-center justify-between mb-3">
                    <span className="kpi-label">{kpi.label}</span>
                    <span className={`status-badge ${isGood ? 'status-current' : 'status-loss'}`}>
                      {isGood ? 'PASS' : 'BREACH'}
                    </span>
                  </div>
                  <div className="kpi-value">{kpi.value}{kpi.unit}</div>
                  {/* Progress bar */}
                  <div className="mt-3 h-2 rounded-full" style={{ background: 'var(--surface-bg)' }}>
                    <div className={`h-full rounded-full transition-all duration-1000 ${
                      isGood ? 'bg-status-current' : 'bg-status-loss'
                    }`} style={{ width: `${pct}%` }} />
                  </div>
                  <div className="flex justify-between text-xs text-content-muted mt-1">
                    <span>{kpi.min ? `Min: ${kpi.min}%` : ''}</span>
                    <span>{kpi.max ? `Max: ${kpi.max}%` : ''}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Large Exposures + Audit Findings */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card">
              <span className="card-title">Top 5 Exposures (% of capital)</span>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={largeExposures} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--content-muted)' }} unit="%" />
                  <YAxis type="category" dataKey="borrower" width={140}
                         tick={{ fontSize: 11, fill: 'var(--content-secondary)' }} />
                  <Tooltip contentStyle={{ background: 'var(--surface-card)', border: '1px solid var(--surface-border)', borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="pctCapital" name="% of Capital" fill="var(--brand-primary)" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card">
              <span className="card-title">Open audit findings</span>
              <div className="space-y-3">
                {auditFindings.map((f, i) => (
                  <div key={i} className="flex items-start gap-3 py-2 border-b border-surface-border last:border-0">
                    <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
                      f.severity === 'HIGH' ? 'bg-status-loss' :
                      f.severity === 'MEDIUM' ? 'bg-status-watch' : 'bg-status-current'
                    }`} />
                    <div className="flex-1">
                      <div className="text-xs font-semibold text-content-primary">{f.finding}</div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-content-muted">
                        <span className={`status-badge ${
                          f.status === 'OPEN' ? 'status-loss' :
                          f.status === 'UNDER_REVIEW' ? 'status-watch' : 'status-current'
                        }`}>{f.status}</span>
                        <span>{f.age}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* INSIDER LENDING TAB */}
      {activeTab === 'insiders' && (
        <div className="space-y-4">
          <div className="card">
            <span className="card-title">Insider lending register</span>
            <p className="text-xs text-content-muted mb-4">
              All loans to directors, senior management, shareholders, and related parties.
              Regulatory limit: 5% of capital per insider.
            </p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-content-muted uppercase tracking-wider">
                  <th className="text-left py-2">Name & Relationship</th>
                  <th className="text-right py-2">Outstanding</th>
                  <th className="text-right py-2">Limit</th>
                  <th className="text-right py-2">Utilisation</th>
                  <th className="text-right py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {insiderLoans.map((loan, i) => {
                  const utilisation = (loan.outstanding / loan.limit * 100);
                  return (
                    <tr key={i} className="border-t border-surface-border">
                      <td className="py-3">
                        <div className="font-semibold text-content-primary">{loan.name}</div>
                        <div className="text-xs text-content-muted">{loan.relationship}</div>
                      </td>
                      <td className="py-3 text-right text-content-secondary">{formatGHS(loan.outstanding)}</td>
                      <td className="py-3 text-right text-content-muted">{formatGHS(loan.limit)}</td>
                      <td className="py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <div className="w-16 h-1.5 rounded-full" style={{ background: 'var(--surface-bg)' }}>
                            <div className={`h-full rounded-full ${
                              utilisation > 80 ? 'bg-status-loss' : utilisation > 60 ? 'bg-status-watch' : 'bg-status-current'
                            }`} style={{ width: `${Math.min(utilisation, 100)}%` }} />
                          </div>
                          <span className="text-xs font-bold">{utilisation.toFixed(0)}%</span>
                        </div>
                      </td>
                      <td className="py-3 text-right">
                        <span className={`status-badge ${
                          loan.status === 'APPROACHING' ? 'status-watch' : 'status-current'
                        }`}>
                          {loan.status === 'APPROACHING' ? 'APPROACHING' : 'OK'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* RISK REGISTER TAB */}
      {activeTab === 'risk' && (
        <div className="card">
          <span className="card-title">Institutional risk register</span>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-content-muted uppercase tracking-wider">
                <th className="text-left py-2">Risk</th>
                <th className="text-center py-2">Likelihood</th>
                <th className="text-center py-2">Impact</th>
                <th className="text-left py-2">Owner</th>
                <th className="text-center py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {riskRegister.map((risk, i) => (
                <tr key={i} className="border-t border-surface-border">
                  <td className="py-3 text-content-primary font-medium">{risk.risk}</td>
                  <td className="py-3 text-center">
                    <span className={`status-badge ${
                      risk.likelihood === 'HIGH' ? 'status-loss' : risk.likelihood === 'MEDIUM' ? 'status-watch' : 'status-current'
                    }`}>{risk.likelihood}</span>
                  </td>
                  <td className="py-3 text-center">
                    <span className={`status-badge ${
                      risk.impact === 'HIGH' ? 'status-loss' : risk.impact === 'MEDIUM' ? 'status-watch' : 'status-current'
                    }`}>{risk.impact}</span>
                  </td>
                  <td className="py-3 text-content-secondary">{risk.owner}</td>
                  <td className="py-3 text-center">
                    <span className="text-xs font-semibold text-content-muted">{risk.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* BOARD PACK TAB */}
      {activeTab === 'board_pack' && (
        <div className="card max-w-2xl">
          <span className="card-title">Generate board pack</span>
          <p className="text-sm text-content-secondary mb-6">
            The board pack combines all governance metrics, risk analysis, financial statements,
            and compliance status into a single branded PDF document.
          </p>
          <div className="space-y-3 mb-6">
            {[
              'Executive Summary & KPIs',
              'Capital Adequacy & Liquidity Position',
              'Portfolio Quality (PAR, Classification, Provisioning)',
              'Insider Lending Register',
              'Large Exposure Report',
              'Compliance Status & Regulatory Returns',
              'Open Audit Findings',
              'Risk Register',
              'Financial Statements (P&L, Balance Sheet)',
            ].map((section, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-surface-border last:border-0">
                <CheckCircle className="w-4 h-4 text-status-current" />
                <span className="text-sm text-content-primary">{section}</span>
              </div>
            ))}
          </div>
          <button className="btn-primary">
            <Download className="w-4 h-4" /> Generate Board Pack PDF
          </button>
        </div>
      )}
    </div>
  );
}
