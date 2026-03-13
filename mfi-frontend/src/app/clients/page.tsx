'use client';
import { useState, useMemo } from 'react';
import Link from 'next/link';
import {
  Search, Filter, Plus, Download, Upload, ChevronDown,
  Eye, Edit, FileText, Phone, AlertTriangle, Check, X,
  UserPlus, Users
} from 'lucide-react';
import type { ClientListItem } from '@/types';

// Mock data — replaced by API + offline cache in production
const mockClients: ClientListItem[] = Array.from({ length: 25 }, (_, i) => ({
  id: `client-${i}`,
  client_number: `CL-${String(i + 1).padStart(5, '0')}`,
  full_legal_name: ['Kwame Asante', 'Ama Mensah', 'Kofi Owusu', 'Abena Boateng', 'Yaw Frimpong',
    'Adwoa Sarpong', 'Nana Agyemang', 'Efua Darko', 'Kwesi Ampofo', 'Akua Osei',
    'Emmanuel Tetteh', 'Patience Adjei', 'Samuel Appiah', 'Grace Addo', 'Francis Mensah',
    'Elizabeth Ankah', 'Daniel Badu', 'Mercy Asantewaa', 'Joseph Ofori', 'Lydia Gyamfi',
    'Michael Antwi', 'Felicia Boakye', 'Richard Adu', 'Victoria Essien', 'Isaac Bonsu'][i],
  client_type: i % 5 === 0 ? 'SME' : i % 7 === 0 ? 'GROUP' : 'INDIVIDUAL',
  phone_primary: `+233 ${20 + (i % 10)}${String(Math.floor(Math.random() * 10000000)).padStart(7, '0')}`,
  kyc_status: i % 8 === 0 ? 'INCOMPLETE' : i % 12 === 0 ? 'EXPIRED' : i % 6 === 0 ? 'COMPLETE' : 'VERIFIED',
  risk_rating: i % 10 === 0 ? 'HIGH' : i % 4 === 0 ? 'MEDIUM' : 'LOW',
  branch_name: ['Accra Main', 'Kumasi', 'Tamale', 'Cape Coast'][i % 4],
  officer_name: ['James Mensah', 'Sarah Asante', 'Peter Owusu', 'Helen Boateng'][i % 4],
  is_insider: i === 3 || i === 15,
  is_pep: i === 7,
  created_at: new Date(2024, i % 12, (i % 28) + 1).toISOString(),
}));

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

  const filtered = useMemo(() => {
    return mockClients.filter(c => {
      if (search && !c.full_legal_name.toLowerCase().includes(search.toLowerCase()) &&
          !c.client_number.toLowerCase().includes(search.toLowerCase()) &&
          !c.phone_primary.includes(search)) return false;
      if (kycFilter && c.kyc_status !== kycFilter) return false;
      if (branchFilter && c.branch_name !== branchFilter) return false;
      return true;
    });
  }, [search, kycFilter, branchFilter]);

  const branches = [...new Set(mockClients.map(c => c.branch_name))];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content-primary">Clients</h1>
          <p className="text-sm text-content-muted mt-1">{mockClients.length} total · {filtered.length} shown</p>
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
