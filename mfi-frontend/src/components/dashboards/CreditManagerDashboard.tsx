'use client';
import { useState } from 'react';
import {
  CheckCircle, Clock, AlertTriangle, Shield, ThumbsUp, ThumbsDown,
  PieChart, Users, BarChart3
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts';

const pendingApprovals = [
  { id: '1', loan: 'LN-202603-00089', client: 'Emmanuel Tetteh', product: 'SME Working Capital', amount: 35000, currency: 'GHS', term: 12, rate: 28, dti: 38, score: 72, risk: 'ACCEPTABLE', officer: 'James Mensah', days_pending: 2, insider: false, override: false },
  { id: '2', loan: 'LN-202603-00090', client: 'Patience Adjei', product: 'Individual Micro', amount: 3500, currency: 'GHS', term: 6, rate: 30, dti: 25, score: 85, risk: 'LOW_RISK', officer: 'Sarah Asante', days_pending: 1, insider: false, override: false },
  { id: '3', loan: 'LN-202603-00091', client: 'Daniel Badu (Director spouse)', product: 'Individual Micro', amount: 8000, currency: 'GHS', term: 12, rate: 24, dti: 42, score: 65, risk: 'ACCEPTABLE', officer: 'Peter Owusu', days_pending: 3, insider: true, override: false },
  { id: '4', loan: 'LN-202603-00092', client: 'Victoria Essien', product: 'Emergency Loan', amount: 800, currency: 'GHS', term: 3, rate: 35, dti: 55, score: 48, risk: 'MEDIUM_RISK', officer: 'Helen Boateng', days_pending: 2, insider: false, override: true },
];

const provisioningSummary = [
  { classification: 'Current', count: 1025, outstanding: 4308560, rate: 1, provision: 43086, color: '#10b981' },
  { classification: 'Watch', count: 102, outstanding: 429261, rate: 5, provision: 21463, color: '#f59e0b' },
  { classification: 'Substandard', count: 64, outstanding: 266979, rate: 25, provision: 66745, color: '#f97316' },
  { classification: 'Doubtful', count: 38, outstanding: 167516, rate: 50, provision: 83758, color: '#ef4444' },
  { classification: 'Loss', count: 18, outstanding: 62819, rate: 100, provision: 62819, color: '#dc2626' },
];

const concentrationData = [
  { sector: 'Trading', pct: 34, color: '#0066ff' },
  { sector: 'Agriculture', pct: 22, color: '#10b981' },
  { sector: 'Services', pct: 18, color: '#8b5cf6' },
  { sector: 'Manufacturing', pct: 14, color: '#f59e0b' },
  { sector: 'Construction', pct: 8, color: '#06b6d4' },
  { sector: 'Other', pct: 4, color: '#64748b' },
];

const riskColors: Record<string, string> = {
  LOW_RISK: 'status-current', ACCEPTABLE: 'bg-blue-500/15 text-blue-400',
  MEDIUM_RISK: 'status-watch', HIGH_RISK: 'status-loss',
};

function fmt(v: number) { return `GHS ${v.toLocaleString()}`; }

export default function CreditManagerDashboard() {
  const [tab, setTab] = useState('pipeline');
  const totalProv = provisioningSummary.reduce((s, p) => s + p.provision, 0);
  const totalOut = provisioningSummary.reduce((s, p) => s + p.outstanding, 0);

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-content-primary">Credit Manager Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="kpi-card"><div className="kpi-label">Pending Approval</div><div className="kpi-value text-status-watch">{pendingApprovals.length}</div></div>
        <div className="kpi-card"><div className="kpi-label">Total Provisions</div><div className="kpi-value">{fmt(totalProv)}</div></div>
        <div className="kpi-card"><div className="kpi-label">NPL Ratio</div><div className="kpi-value text-status-watch">4.1%</div></div>
        <div className="kpi-card"><div className="kpi-label">Coverage Ratio</div><div className="kpi-value">{(totalProv / totalOut * 100).toFixed(1)}%</div></div>
      </div>

      <div className="flex gap-1 border-b border-surface-border">
        {[{k:'pipeline',l:'Pipeline',b:pendingApprovals.length},{k:'provisioning',l:'Provisioning'},{k:'concentration',l:'Concentration'}].map(t=>(
          <button key={t.k} onClick={()=>setTab(t.k)} className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 ${tab===t.k?'border-brand-primary text-content-primary':'border-transparent text-content-muted'}`}>
            {t.l}{t.b&&<span className="ml-1 w-5 h-5 bg-status-watch text-white text-xs font-bold rounded-full flex items-center justify-center">{t.b}</span>}
          </button>
        ))}
      </div>

      {tab === 'pipeline' && (
        <div className="space-y-3">
          {pendingApprovals.map(loan => (
            <div key={loan.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-content-primary">{loan.client}</span>
                    {loan.insider && <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-purple-500/15 text-purple-400">INSIDER</span>}
                    {loan.override && <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-status-watch/15 text-status-watch">OVERRIDE</span>}
                  </div>
                  <div className="text-xs text-content-muted mt-0.5">{loan.loan} · {loan.product} · by {loan.officer}</div>
                </div>
                <span className={`status-badge ${riskColors[loan.risk]}`}>{loan.risk.replace('_', ' ')}</span>
              </div>
              <div className="grid grid-cols-6 gap-3 mb-3">
                {[['Amount',fmt(loan.amount)],['Term',`${loan.term}m`],['Rate',`${loan.rate}%`],['DTI',`${loan.dti}%`],['Score',`${loan.score}/100`],['Pending',`${loan.days_pending}d`]].map(([l,v],i)=>(
                  <div key={i} className="text-center p-2 rounded-lg" style={{background:'var(--surface-hover)'}}>
                    <div className="text-xs text-content-muted">{l}</div>
                    <div className="text-sm font-bold text-content-primary">{v}</div>
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2">
                <button className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-status-loss hover:bg-status-loss/10"><ThumbsDown className="w-3.5 h-3.5"/>Reject</button>
                <button className="btn-primary text-xs"><ThumbsUp className="w-3.5 h-3.5"/>Approve</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'provisioning' && (
        <div className="card">
          <span className="card-title">Provision requirements by classification</span>
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-content-muted uppercase tracking-wider">
              <th className="text-left py-2">Classification</th><th className="text-right py-2">Loans</th>
              <th className="text-right py-2">Outstanding</th><th className="text-right py-2">Rate</th>
              <th className="text-right py-2">Provision Required</th>
            </tr></thead>
            <tbody>
              {provisioningSummary.map(p=>(
                <tr key={p.classification} className="border-t border-surface-border">
                  <td className="py-3"><span className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{background:p.color}}/>{p.classification}</span></td>
                  <td className="py-3 text-right">{p.count}</td>
                  <td className="py-3 text-right font-semibold">{fmt(p.outstanding)}</td>
                  <td className="py-3 text-right text-content-muted">{p.rate}%</td>
                  <td className="py-3 text-right font-bold" style={{color:p.color}}>{fmt(p.provision)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'concentration' && (
        <div className="card">
          <span className="card-title">Sector concentration</span>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={concentrationData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--surface-border)"/>
              <XAxis type="number" unit="%" tick={{fontSize:11,fill:'var(--content-muted)'}}/>
              <YAxis type="category" dataKey="sector" width={100} tick={{fontSize:11,fill:'var(--content-secondary)'}}/>
              <Tooltip contentStyle={{background:'var(--surface-card)',border:'1px solid var(--surface-border)',borderRadius:8,fontSize:12}}/>
              <Bar dataKey="pct" name="% of Portfolio" radius={[0,4,4,0]}>
                {concentrationData.map((d,i)=><Cell key={i} fill={d.color}/>)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
