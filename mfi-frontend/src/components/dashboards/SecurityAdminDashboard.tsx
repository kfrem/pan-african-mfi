'use client';
import { useState } from 'react';
import {
  Shield, Lock, Users, Monitor, AlertTriangle, Eye,
  LogIn, LogOut, RefreshCw, Ban, Globe, Clock, Key
} from 'lucide-react';

const activeSessions = [
  { user: 'James Mensah', role: 'LOAN_OFFICER', ip: '41.215.34.12', device: 'Chrome / Android', location: 'Accra, GH', started: '08:15', lastActivity: '2min ago', active: true },
  { user: 'Sarah Asante', role: 'LOAN_OFFICER', ip: '41.215.89.45', device: 'Safari / iPhone', location: 'Kumasi, GH', started: '07:30', lastActivity: '5min ago', active: true },
  { user: 'Peter Owusu', role: 'BRANCH_MANAGER', ip: '41.215.67.23', device: 'Chrome / Windows', location: 'Tamale, GH', started: '09:00', lastActivity: '1min ago', active: true },
  { user: 'Helen Boateng', role: 'ACCOUNTANT', ip: '41.215.12.78', device: 'Firefox / Windows', location: 'Accra, GH', started: '08:45', lastActivity: '12min ago', active: true },
  { user: 'CEO Dashboard', role: 'CEO_CFO', ip: '196.12.45.67', device: 'Chrome / macOS', location: 'London, GB', started: '10:30', lastActivity: '3min ago', active: true },
];

const loginAttempts = [
  { email: 'james@accramfi.com', success: true, ip: '41.215.34.12', time: '08:15', reason: '' },
  { email: 'unknown@gmail.com', success: false, ip: '185.92.34.56', time: '07:58', reason: 'WRONG_PASSWORD' },
  { email: 'unknown@gmail.com', success: false, ip: '185.92.34.56', time: '07:57', reason: 'WRONG_PASSWORD' },
  { email: 'unknown@gmail.com', success: false, ip: '185.92.34.56', time: '07:56', reason: 'WRONG_PASSWORD' },
  { email: 'sarah@accramfi.com', success: true, ip: '41.215.89.45', time: '07:30', reason: '' },
  { email: 'locked.user@accramfi.com', success: false, ip: '41.215.55.12', time: '06:45', reason: 'LOCKED' },
];

const userProvisioning = [
  { action: 'CREATED', user: 'New Officer (Mary Ansah)', role: 'LOAN_OFFICER', by: 'Peter Owusu', date: '2026-03-12' },
  { action: 'ROLE_CHANGED', user: 'Helen Boateng', role: 'ACCOUNTANT → CEO_CFO', by: 'System Admin', date: '2026-03-10' },
  { action: 'DEACTIVATED', user: 'Former Staff (Kofi Adu)', role: 'LOAN_OFFICER', by: 'Peter Owusu', date: '2026-03-08' },
  { action: 'MFA_ENABLED', user: 'CEO Dashboard', role: 'CEO_CFO', by: 'Self', date: '2026-03-05' },
];

const securityAlerts = [
  { severity: 'HIGH', message: '3 consecutive failed logins from IP 185.92.34.56 (non-GH origin)', time: '07:58', action: 'IP blocked for 1 hour' },
  { severity: 'MEDIUM', message: 'CEO session active from non-whitelisted IP (London)', time: '10:30', action: 'Monitoring' },
  { severity: 'LOW', message: 'Locked account login attempt: locked.user@accramfi.com', time: '06:45', action: 'Logged' },
];

export default function SecurityAdminDashboard() {
  const [tab, setTab] = useState('sessions');

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-content-primary">IT Security Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="kpi-card"><div className="kpi-label">Active Sessions</div><div className="kpi-value">{activeSessions.length}</div></div>
        <div className="kpi-card"><div className="kpi-label">Failed Logins (24h)</div><div className="kpi-value text-status-loss">{loginAttempts.filter(l=>!l.success).length}</div></div>
        <div className="kpi-card"><div className="kpi-label">Security Alerts</div><div className="kpi-value text-status-watch">{securityAlerts.length}</div></div>
        <div className="kpi-card"><div className="kpi-label">Locked Accounts</div><div className="kpi-value">1</div></div>
        <div className="kpi-card"><div className="kpi-label">MFA Enabled</div><div className="kpi-value text-status-current">68%</div></div>
      </div>

      <div className="flex gap-1 border-b border-surface-border">
        {[{k:'sessions',l:'Active Sessions',i:Monitor},{k:'logins',l:'Login Log',i:LogIn},{k:'provisioning',l:'User Changes',i:Users},{k:'alerts',l:'Security Alerts',i:AlertTriangle}].map(t=>(
          <button key={t.k} onClick={()=>setTab(t.k)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 ${tab===t.k?'border-brand-primary text-content-primary':'border-transparent text-content-muted'}`}>
            <t.i className="w-3.5 h-3.5"/>{t.l}
          </button>
        ))}
      </div>

      {tab === 'sessions' && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-content-muted uppercase tracking-wider bg-surface-hover">
              <th className="text-left py-3 px-4">User</th><th className="text-left py-3 px-3">Role</th>
              <th className="text-left py-3 px-3">IP Address</th><th className="text-left py-3 px-3">Device</th>
              <th className="text-left py-3 px-3">Location</th><th className="text-left py-3 px-3">Last Activity</th>
              <th className="text-right py-3 px-4">Action</th>
            </tr></thead>
            <tbody>
              {activeSessions.map((s,i)=>(
                <tr key={i} className="border-t border-surface-border">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-status-current animate-pulse-soft"/>
                      <span className="font-semibold text-content-primary">{s.user}</span>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-xs text-content-muted">{s.role}</td>
                  <td className="py-3 px-3 font-mono text-xs text-content-secondary">{s.ip}</td>
                  <td className="py-3 px-3 text-xs text-content-muted">{s.device}</td>
                  <td className="py-3 px-3 text-xs text-content-secondary">
                    <span className="flex items-center gap-1"><Globe className="w-3 h-3"/>{s.location}</span>
                  </td>
                  <td className="py-3 px-3 text-xs text-content-muted">{s.lastActivity}</td>
                  <td className="py-3 px-4 text-right">
                    <button className="px-2 py-1 rounded text-xs font-semibold text-status-loss hover:bg-status-loss/10">
                      <Ban className="w-3 h-3 inline mr-1"/>Kill
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'logins' && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead><tr className="text-xs text-content-muted uppercase tracking-wider bg-surface-hover">
              <th className="text-left py-3 px-4">Time</th><th className="text-left py-3 px-3">Email</th>
              <th className="text-center py-3 px-3">Result</th><th className="text-left py-3 px-3">IP</th>
              <th className="text-left py-3 px-3">Reason</th>
            </tr></thead>
            <tbody>
              {loginAttempts.map((l,i)=>(
                <tr key={i} className="border-t border-surface-border">
                  <td className="py-3 px-4 text-xs text-content-muted">{l.time}</td>
                  <td className="py-3 px-3 text-content-primary">{l.email}</td>
                  <td className="py-3 px-3 text-center">
                    {l.success
                      ? <span className="status-badge status-current">OK</span>
                      : <span className="status-badge status-loss">FAIL</span>}
                  </td>
                  <td className="py-3 px-3 font-mono text-xs text-content-muted">{l.ip}</td>
                  <td className="py-3 px-3 text-xs text-status-loss">{l.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'provisioning' && (
        <div className="card">
          <span className="card-title">User provisioning log</span>
          <div className="space-y-3">
            {userProvisioning.map((p,i)=>(
              <div key={i} className="flex items-center gap-3 py-2 border-b border-surface-border last:border-0">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                  p.action==='CREATED'?'bg-status-current/15':'bg-surface-hover'}`}>
                  {p.action==='CREATED'?<Users className="w-4 h-4 text-status-current"/>:
                   p.action==='DEACTIVATED'?<Ban className="w-4 h-4 text-status-loss"/>:
                   <Key className="w-4 h-4 text-content-muted"/>}
                </div>
                <div className="flex-1">
                  <div className="text-sm text-content-primary"><span className="font-semibold">{p.user}</span> — {p.role}</div>
                  <div className="text-xs text-content-muted">{p.action} by {p.by} on {p.date}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'alerts' && (
        <div className="space-y-3">
          {securityAlerts.map((a,i)=>(
            <div key={i} className="card flex items-start gap-3">
              <div className={`w-2 h-2 rounded-full mt-1.5 ${a.severity==='HIGH'?'bg-status-loss':a.severity==='MEDIUM'?'bg-status-watch':'bg-blue-400'}`}/>
              <div className="flex-1">
                <div className="text-sm text-content-primary">{a.message}</div>
                <div className="flex items-center gap-3 mt-1 text-xs text-content-muted">
                  <span>{a.time}</span><span>Action: {a.action}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
