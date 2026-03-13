'use client';
import { useState } from 'react';
import {
  BookOpen, Calculator, CheckSquare, FileText, Download,
  Lock, Unlock, AlertTriangle, Search, ChevronRight
} from 'lucide-react';

const trialBalance = [
  { code: '1000', name: 'Cash and Bank Balances', type: 'ASSET', debit: 2350000, credit: 0 },
  { code: '1100', name: 'Loans Receivable', type: 'ASSET', debit: 5234890, credit: 0 },
  { code: '1200', name: 'Provision for Loan Losses', type: 'ASSET', debit: 0, credit: 277871 },
  { code: '1300', name: 'Other Assets', type: 'ASSET', debit: 450000, credit: 0 },
  { code: '2000', name: 'Customer Deposits', type: 'LIABILITY', debit: 0, credit: 3800000 },
  { code: '2100', name: 'Borrowings', type: 'LIABILITY', debit: 0, credit: 1500000 },
  { code: '2200', name: 'Other Liabilities', type: 'LIABILITY', debit: 0, credit: 320000 },
  { code: '3000', name: 'Paid-Up Capital', type: 'EQUITY', debit: 0, credit: 2000000 },
  { code: '3100', name: 'Retained Earnings', type: 'EQUITY', debit: 0, credit: 425019 },
  { code: '4000', name: 'Interest Income', type: 'INCOME', debit: 0, credit: 1850000 },
  { code: '4100', name: 'Fee Income', type: 'INCOME', debit: 0, credit: 285000 },
  { code: '5000', name: 'Interest Expense', type: 'EXPENSE', debit: 380000, credit: 0 },
  { code: '5100', name: 'Operating Expenses', type: 'EXPENSE', debit: 920000, credit: 0 },
  { code: '5200', name: 'Provision Expense', type: 'EXPENSE', debit: 148000, credit: 0 },
  { code: '5300', name: 'Staff Costs', type: 'EXPENSE', debit: 975000, credit: 0 },
];

const reconItems = [
  { date: '2026-03-08', description: 'Mobile money settlement — MTN MoMo', systemAmt: 45200, bankAmt: 45200, matched: true },
  { date: '2026-03-09', description: 'Cash deposit — Branch Kumasi', systemAmt: 12500, bankAmt: 0, matched: false },
  { date: '2026-03-10', description: 'Bank charges', systemAmt: 0, bankAmt: 350, matched: false },
  { date: '2026-03-11', description: 'Loan disbursement — LN-202603-00087', systemAmt: 15000, bankAmt: 15000, matched: true },
  { date: '2026-03-12', description: 'Transfer from head office', systemAmt: 0, bankAmt: 50000, matched: false },
];

const periods = [
  { name: '2026-03', label: 'March 2026', status: 'OPEN', start: '2026-03-01', end: '2026-03-31' },
  { name: '2026-02', label: 'February 2026', status: 'CLOSED', start: '2026-02-01', end: '2026-02-28' },
  { name: '2026-01', label: 'January 2026', status: 'CLOSED', start: '2026-01-01', end: '2026-01-31' },
  { name: '2025-12', label: 'December 2025', status: 'CLOSED', start: '2025-12-01', end: '2025-12-31' },
];

function formatGHS(v: number) { return `GHS ${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }

export default function AccountantDashboard() {
  const [activeTab, setActiveTab] = useState('trial_balance');
  const [glSearch, setGlSearch] = useState('');

  const totalDebits = trialBalance.reduce((s, a) => s + a.debit, 0);
  const totalCredits = trialBalance.reduce((s, a) => s + a.credit, 0);
  const isBalanced = Math.abs(totalDebits - totalCredits) < 0.01;
  const unmatchedRecon = reconItems.filter(r => !r.matched).length;

  const tabs = [
    { key: 'trial_balance', label: 'Trial Balance', icon: Calculator },
    { key: 'reconciliation', label: 'Reconciliation', icon: CheckSquare, badge: unmatchedRecon },
    { key: 'period_close', label: 'Period Close', icon: Lock },
    { key: 'statements', label: 'Financial Statements', icon: FileText },
  ];

  const filteredTB = glSearch
    ? trialBalance.filter(a => a.name.toLowerCase().includes(glSearch.toLowerCase()) || a.code.includes(glSearch))
    : trialBalance;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">Accounting</h1>
          <p className="text-sm text-content-muted mt-1">General ledger · Trial balance · Reconciliations</p>
        </div>
        <button className="btn-primary text-xs"><Download className="w-3.5 h-3.5" /> Export Statements</button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="kpi-card">
          <div className="kpi-label">Trial Balance</div>
          <div className={`kpi-value ${isBalanced ? 'text-status-current' : 'text-status-loss'}`}>
            {isBalanced ? 'Balanced' : 'Imbalanced'}
          </div>
          <div className="text-xs text-content-muted mt-1">Debits: {formatGHS(totalDebits)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Unreconciled Items</div>
          <div className={`kpi-value ${unmatchedRecon > 0 ? 'text-status-watch' : 'text-status-current'}`}>{unmatchedRecon}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Current Period</div>
          <div className="kpi-value">{periods[0].label}</div>
          <div className="text-xs text-content-muted mt-1">
            <span className="status-badge status-current">{periods[0].status}</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Net Income (MTD)</div>
          <div className="kpi-value text-status-current">{formatGHS(totalCredits - totalDebits > 0 ? 712000 : 0)}</div>
        </div>
      </div>

      <div className="flex gap-1 border-b border-surface-border">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
                    activeTab === tab.key ? 'border-brand-primary text-content-primary' : 'border-transparent text-content-muted'
                  }`}>
            <tab.icon className="w-3.5 h-3.5" /> {tab.label}
            {tab.badge && <span className="ml-1 w-5 h-5 bg-status-watch text-white text-xs font-bold rounded-full flex items-center justify-center">{tab.badge}</span>}
          </button>
        ))}
      </div>

      {/* TRIAL BALANCE */}
      {activeTab === 'trial_balance' && (
        <div className="card p-0 overflow-hidden">
          <div className="p-4 border-b border-surface-border">
            <div className="relative max-w-sm">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-content-muted" />
              <input type="text" value={glSearch} onChange={e => setGlSearch(e.target.value)}
                     placeholder="Search accounts..."
                     className="w-full pl-10 pr-4 py-2 rounded-lg text-sm bg-surface-bg border border-surface-border text-content-primary" />
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-content-muted uppercase tracking-wider bg-surface-hover">
                <th className="text-left py-2.5 px-4">Code</th>
                <th className="text-left py-2.5 px-3">Account Name</th>
                <th className="text-center py-2.5 px-3">Type</th>
                <th className="text-right py-2.5 px-3">Debit</th>
                <th className="text-right py-2.5 px-4">Credit</th>
              </tr>
            </thead>
            <tbody>
              {filteredTB.map(a => (
                <tr key={a.code} className="border-t border-surface-border hover:bg-surface-hover cursor-pointer">
                  <td className="py-2.5 px-4 font-mono text-xs font-semibold">{a.code}</td>
                  <td className="py-2.5 px-3 text-content-primary font-medium">{a.name}</td>
                  <td className="py-2.5 px-3 text-center">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                      a.type === 'ASSET' ? 'bg-blue-500/10 text-blue-400' :
                      a.type === 'LIABILITY' ? 'bg-purple-500/10 text-purple-400' :
                      a.type === 'EQUITY' ? 'bg-teal-500/10 text-teal-400' :
                      a.type === 'INCOME' ? 'bg-green-500/10 text-green-400' :
                      'bg-orange-500/10 text-orange-400'
                    }`}>{a.type}</span>
                  </td>
                  <td className="py-2.5 px-3 text-right font-mono">{a.debit > 0 ? formatGHS(a.debit) : ''}</td>
                  <td className="py-2.5 px-4 text-right font-mono">{a.credit > 0 ? formatGHS(a.credit) : ''}</td>
                </tr>
              ))}
              <tr className="border-t-2 border-surface-border font-bold bg-surface-hover">
                <td colSpan={3} className="py-3 px-4">TOTAL</td>
                <td className="py-3 px-3 text-right font-mono">{formatGHS(totalDebits)}</td>
                <td className="py-3 px-4 text-right font-mono">{formatGHS(totalCredits)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* RECONCILIATION */}
      {activeTab === 'reconciliation' && (
        <div className="card">
          <span className="card-title">Bank reconciliation — Main operating account</span>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-content-muted uppercase tracking-wider">
                <th className="text-left py-2">Date</th>
                <th className="text-left py-2">Description</th>
                <th className="text-right py-2">System</th>
                <th className="text-right py-2">Bank</th>
                <th className="text-center py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {reconItems.map((r, i) => (
                <tr key={i} className={`border-t border-surface-border ${!r.matched ? 'bg-status-watch/5' : ''}`}>
                  <td className="py-2.5 text-xs">{r.date}</td>
                  <td className="py-2.5 text-content-primary">{r.description}</td>
                  <td className="py-2.5 text-right font-mono">{r.systemAmt > 0 ? formatGHS(r.systemAmt) : '—'}</td>
                  <td className="py-2.5 text-right font-mono">{r.bankAmt > 0 ? formatGHS(r.bankAmt) : '—'}</td>
                  <td className="py-2.5 text-center">
                    <span className={`status-badge ${r.matched ? 'status-current' : 'status-watch'}`}>
                      {r.matched ? 'MATCHED' : 'UNMATCHED'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PERIOD CLOSE */}
      {activeTab === 'period_close' && (
        <div className="card">
          <span className="card-title">Accounting periods</span>
          <div className="space-y-3">
            {periods.map(p => (
              <div key={p.name} className="flex items-center justify-between py-3 border-b border-surface-border last:border-0">
                <div className="flex items-center gap-3">
                  {p.status === 'OPEN' ? (
                    <Unlock className="w-4 h-4 text-status-current" />
                  ) : (
                    <Lock className="w-4 h-4 text-content-muted" />
                  )}
                  <div>
                    <div className="font-semibold text-content-primary text-sm">{p.label}</div>
                    <div className="text-xs text-content-muted">{p.start} to {p.end}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`status-badge ${p.status === 'OPEN' ? 'status-current' : 'bg-gray-500/15 text-gray-400'}`}>
                    {p.status}
                  </span>
                  {p.status === 'OPEN' && (
                    <button className="btn-secondary text-xs py-1"><Lock className="w-3 h-3" /> Close Period</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* FINANCIAL STATEMENTS */}
      {activeTab === 'statements' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[
            { title: 'Income Statement', description: 'Revenue, expenses, and net income for the selected period', icon: TrendingUp },
            { title: 'Balance Sheet', description: 'Assets, liabilities, and equity as of period end', icon: BookOpen },
            { title: 'Cash Flow Statement', description: 'Cash inflows and outflows by category', icon: FileText },
          ].map(stmt => (
            <div key={stmt.title} className="card hover:border-brand-primary transition-colors cursor-pointer">
              <stmt.icon className="w-8 h-8 mb-3" style={{ color: 'var(--brand-primary)' }} />
              <h3 className="font-semibold text-content-primary mb-1">{stmt.title}</h3>
              <p className="text-xs text-content-muted mb-4">{stmt.description}</p>
              <div className="flex gap-2">
                <button className="btn-secondary text-xs py-1"><Eye className="w-3 h-3" /> View</button>
                <button className="btn-secondary text-xs py-1"><Download className="w-3 h-3" /> PDF</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
