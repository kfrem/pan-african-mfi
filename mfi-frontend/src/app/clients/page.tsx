'use client';
import { useState, useMemo, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Search, Filter, Plus, Download, Upload, ChevronDown,
  Eye, Edit, FileText, Phone, AlertTriangle, Check, X,
  UserPlus, Users, Loader2
} from 'lucide-react';
import type { ClientListItem } from '@/types';
import { apiService } from '@/lib/api-service';

const kycColors: Record<string, string> = {
  VERIFIED: 'status-current', COMPLETE: 'text-blue-400 bg-blue-400/15',
  INCOMPLETE: 'status-watch', EXPIRED: 'status-loss',
};
const riskColors: Record<string, string> = {
  LOW: 'status-current', MEDIUM: 'status-watch', HIGH: 'status-loss',
};

export default function ClientsPage() {
  const [search, setSearch] = useState('');
  const [kycFilter, setKycFilter] = useState<string>('');
  const [branchFilter, setBranchFilter] = useState<string>('');
  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [apiAvailable, setApiAvailable] = useState(true);

  const loadClients = useCallback(async () => {
    setLoading(true);
    const result = await apiService.getClients({
      search: search || undefined,
      kyc_status: kycFilter || undefined,
    });
    if (result) {
      setClients(result.results as unknown as ClientListItem[]);
      setTotalCount(result.count);
      setApiAvailable(true);
    } else {
      setApiAvailable(false);
    }
    setLoading(false);
  }, [search, kycFilter]);

  useEffect(() => {
    const timer = setTimeout(loadClients, 300);
    return () => clearTimeout(timer);
  }, [loadClients]);

  // Client-side branch filter when API doesn't support it
  const filtered = useMemo(() => {
    if (!branchFilter) return clients;
    return clients.filter(c => c.branch_name === branchFilter);
  }, [clients, branchFilter]);

  const branches = [...new Set(clients.map(c => c.branch_name).filter(Boolean))];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">Clients</h1>
          <p className="text-sm text-content-muted mt-1">
            {loading ? (
              <span className="flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" /> Loading...</span>
            ) : (
              `${totalCount} total · ${filtered.length} shown${!apiAvailable ? ' (offline)' : ''}`
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button className="btn-secondary text-xs"><Upload className="w-3.5 h-3.5" /> Import CSV</button>
          <button className="btn-secondary text-xs"><Download className="w-3.5 h-3.5" /> Export</button>
          <Link href="/clients/new" className="btn-primary text-xs">
            <UserPlus className="w-3.5 h-3.5" /> New Client
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-content-muted" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
                 placeholder="Search by name, ID, or phone..."
                 className="w-full pl-10 pr-4 py-2 rounded-lg text-sm bg-surface-card border border-surface-border text-content-primary placeholder:text-content-muted focus:outline-none focus:border-brand-primary" />
        </div>
        <select value={kycFilter} onChange={e => setKycFilter(e.target.value)}
                className="px-3 py-2 rounded-lg text-xs font-semibold bg-surface-card border border-surface-border text-content-secondary">
          <option value="">All KYC Status</option>
          <option value="VERIFIED">Verified</option>
          <option value="COMPLETE">Complete</option>
          <option value="INCOMPLETE">Incomplete</option>
          <option value="EXPIRED">Expired</option>
        </select>
        <select value={branchFilter} onChange={e => setBranchFilter(e.target.value)}
                className="px-3 py-2 rounded-lg text-xs font-semibold bg-surface-card border border-surface-border text-content-secondary">
          <option value="">All Branches</option>
          {branches.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-content-muted uppercase tracking-wider bg-surface-hover">
                <th className="text-left py-3 px-4">Client</th>
                <th className="text-left py-3 px-3">Type</th>
                <th className="text-left py-3 px-3">Phone</th>
                <th className="text-left py-3 px-3">KYC</th>
                <th className="text-left py-3 px-3">Risk</th>
                <th className="text-left py-3 px-3">Branch</th>
                <th className="text-left py-3 px-3">Officer</th>
                <th className="text-left py-3 px-3">Flags</th>
                <th className="text-right py-3 px-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(client => (
                <tr key={client.id}
                    className="border-t border-surface-border hover:bg-surface-hover transition-colors">
                  <td className="py-3 px-4">
                    <Link href={`/clients/${client.id}`} className="hover:text-brand-primary">
                      <div className="font-semibold text-content-primary">{client.full_legal_name}</div>
                      <div className="text-xs text-content-muted">{client.client_number}</div>
                    </Link>
                  </td>
                  <td className="py-3 px-3">
                    <span className="text-xs font-semibold text-content-secondary">{client.client_type}</span>
                  </td>
                  <td className="py-3 px-3 text-content-secondary text-xs">{client.phone_primary}</td>
                  <td className="py-3 px-3">
                    <span className={`status-badge ${kycColors[client.kyc_status] || ''}`}>
                      {client.kyc_status}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <span className={`status-badge ${riskColors[client.risk_rating] || ''}`}>
                      {client.risk_rating}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-xs text-content-secondary">{client.branch_name}</td>
                  <td className="py-3 px-3 text-xs text-content-secondary">{client.officer_name}</td>
                  <td className="py-3 px-3">
                    <div className="flex gap-1">
                      {client.is_insider && (
                        <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-purple-500/15 text-purple-400">
                          INSIDER
                        </span>
                      )}
                      {client.is_pep && (
                        <span className="px-1.5 py-0.5 rounded text-xs font-bold bg-red-500/15 text-red-400">
                          PEP
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Link href={`/clients/${client.id}`}
                            className="p-1.5 rounded-lg hover:bg-surface-hover text-content-muted hover:text-content-primary">
                        <Eye className="w-3.5 h-3.5" />
                      </Link>
                      <Link href={`/clients/${client.id}/edit`}
                            className="p-1.5 rounded-lg hover:bg-surface-hover text-content-muted hover:text-content-primary">
                        <Edit className="w-3.5 h-3.5" />
                      </Link>
                      <Link href={`/loans/new?client=${client.id}`}
                            className="p-1.5 rounded-lg hover:bg-surface-hover text-content-muted hover:text-content-primary">
                        <FileText className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
