/**
 * Typed API service layer — wraps the base ApiClient with domain-specific methods.
 * All methods gracefully handle errors and can fall back to mock data.
 */
import { api } from './supabase';

// ─── TYPES ───

export interface DashboardStats {
  total_portfolio: string;
  total_loans: number;
  total_arrears: string;
  par30_balance: string;
  par30_pct: number;
}

export interface ClientListItem {
  id: string;
  client_number: string;
  full_legal_name: string;
  client_type: 'INDIVIDUAL' | 'SME' | 'GROUP';
  phone_primary: string;
  kyc_status: 'VERIFIED' | 'COMPLETE' | 'INCOMPLETE' | 'EXPIRED';
  risk_rating: 'LOW' | 'MEDIUM' | 'HIGH';
  branch: string;
  branch_name: string;
  officer_name: string;
  is_insider: boolean;
  is_pep: boolean;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LoanListItem {
  id: string;
  loan_number: string;
  client_name: string;
  product_name: string;
  principal_amount: string;
  outstanding_principal: string;
  currency: string;
  status: string;
  classification: string;
  days_past_due: number;
  disbursement_date: string | null;
  officer_name: string;
  branch_name: string;
}

export interface AmlAlert {
  id: string;
  client_name: string;
  alert_type: string;
  trigger_description: string;
  trigger_amount: string | null;
  status: string;
  risk_score: number | null;
  created_at: string;
}

export interface ReportDefinition {
  id: string;
  report_code: string;
  report_name: string;
  category: string;
  output_formats: string[];
  is_active: boolean;
}

export interface ReportRun {
  id: string;
  report_name: string;
  report_code: string;
  output_format: string;
  status: 'QUEUED' | 'GENERATING' | 'COMPLETED' | 'FAILED';
  file_path: string;
  generation_time_ms: number | null;
  generated_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface MobileMoneyTransaction {
  id: string;
  provider_name: string;
  transaction_type: string;
  direction: 'IN' | 'OUT';
  phone_number: string;
  amount: string;
  currency: string;
  client_name: string;
  status: string;
  initiated_at: string;
}

export interface ImportJob {
  id: string;
  import_type: string;
  file_name: string;
  status: string;
  total_rows: number | null;
  valid_rows: number | null;
  error_rows: number | null;
  imported_count: number;
  created_at: string;
}

// ─── API SERVICE ───

export const apiService = {

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats | null> {
    try {
      return await api.get<DashboardStats>('/loans/dashboard_stats/');
    } catch (err) {
      console.warn('Failed to load dashboard stats, using mock data', err);
      return null;
    }
  },

  // Clients
  async getClients(params?: {
    search?: string;
    kyc_status?: string;
    branch?: string;
    officer?: string;
    page?: number;
  }): Promise<PaginatedResponse<ClientListItem> | null> {
    try {
      const queryParams: Record<string, string> = {};
      if (params?.search) queryParams.search = params.search;
      if (params?.kyc_status) queryParams.kyc_status = params.kyc_status;
      if (params?.branch) queryParams.branch = params.branch;
      if (params?.officer) queryParams.officer = params.officer;
      if (params?.page) queryParams.page = String(params.page);
      return await api.get<PaginatedResponse<ClientListItem>>('/clients/', queryParams);
    } catch (err) {
      console.warn('Failed to load clients', err);
      return null;
    }
  },

  async getClient(id: string) {
    try {
      return await api.get(`/clients/${id}/`);
    } catch (err) {
      console.warn('Failed to load client', err);
      return null;
    }
  },

  async createClient(data: Partial<ClientListItem>) {
    return api.post('/clients/', data);
  },

  async verifyKyc(clientId: string) {
    return api.post(`/clients/${clientId}/verify_kyc/`, {});
  },

  // Loans
  async getLoans(params?: {
    status?: string;
    classification?: string;
    client?: string;
    branch?: string;
    officer?: string;
  }): Promise<PaginatedResponse<LoanListItem> | null> {
    try {
      const queryParams: Record<string, string> = {};
      if (params?.status) queryParams.status = params.status;
      if (params?.classification) queryParams.classification = params.classification;
      if (params?.client) queryParams.client = params.client;
      if (params?.branch) queryParams.branch = params.branch;
      if (params?.officer) queryParams.officer = params.officer;
      return await api.get<PaginatedResponse<LoanListItem>>('/loans/', queryParams);
    } catch (err) {
      console.warn('Failed to load loans', err);
      return null;
    }
  },

  async getLoan(id: string) {
    try {
      return await api.get(`/loans/${id}/`);
    } catch (err) {
      console.warn('Failed to load loan', err);
      return null;
    }
  },

  async applyLoan(data: object) {
    return api.post('/loans/apply/', data);
  },

  async approveLoan(loanId: string) {
    return api.post(`/loans/${loanId}/approve/`, {});
  },

  async disburseLoan(loanId: string) {
    return api.post(`/loans/${loanId}/disburse/`, {});
  },

  async captureRepayment(data: {
    loan_id: string;
    amount: string;
    payment_method: string;
    payment_reference?: string;
    received_at: string;
    sync_id?: string;
    device_id?: string;
  }) {
    return api.post('/repayments/capture/', data);
  },

  // AML Alerts
  async getAmlAlerts(params?: { status?: string }) {
    try {
      const queryParams: Record<string, string> = {};
      if (params?.status) queryParams.status = params.status;
      return await api.get<PaginatedResponse<AmlAlert>>('/aml-alerts/', queryParams);
    } catch (err) {
      console.warn('Failed to load AML alerts', err);
      return null;
    }
  },

  async closeAmlAlert(alertId: string, reviewNotes: string) {
    return api.post(`/aml-alerts/${alertId}/close/`, { review_notes: reviewNotes });
  },

  // Reports
  async getReportDefinitions(category?: string): Promise<ReportDefinition[] | null> {
    try {
      const params: Record<string, string> = {};
      if (category) params.category = category;
      const res = await api.get<PaginatedResponse<ReportDefinition> | ReportDefinition[]>(
        '/report-definitions/', params
      );
      // Handle both paginated and non-paginated responses
      if (Array.isArray(res)) return res;
      if ('results' in res) return (res as PaginatedResponse<ReportDefinition>).results;
      return null;
    } catch (err) {
      console.warn('Failed to load report definitions', err);
      return null;
    }
  },

  async getReportRuns(params?: { status?: string; report?: string }) {
    try {
      const queryParams: Record<string, string> = {};
      if (params?.status) queryParams.status = params.status;
      if (params?.report) queryParams.report = params.report;
      return await api.get<PaginatedResponse<ReportRun>>('/report-runs/', queryParams);
    } catch (err) {
      console.warn('Failed to load report runs', err);
      return null;
    }
  },

  async requestReport(reportCode: string, outputFormat: 'PDF' | 'EXCEL' | 'CSV', parameters?: object) {
    return api.post<ReportRun>('/report-runs/request_report/', {
      report_code: reportCode,
      output_format: outputFormat,
      parameters: parameters || {},
    });
  },

  // Mobile Money
  async getMomoTransactions(params?: { status?: string; type?: string; loan?: string }) {
    try {
      const queryParams: Record<string, string> = {};
      if (params?.status) queryParams.status = params.status;
      if (params?.type) queryParams.type = params.type;
      if (params?.loan) queryParams.loan = params.loan;
      return await api.get<PaginatedResponse<MobileMoneyTransaction>>('/momo-transactions/', queryParams);
    } catch (err) {
      console.warn('Failed to load momo transactions', err);
      return null;
    }
  },

  async getMomoProviders(country?: string) {
    try {
      const params: Record<string, string> = {};
      if (country) params.country = country;
      return await api.get('/momo-providers/', params);
    } catch (err) {
      console.warn('Failed to load momo providers', err);
      return null;
    }
  },

  async collectRepayment(data: {
    loan_id: string;
    phone_number: string;
    amount: string;
    provider_code: string;
    device_id?: string;
  }) {
    return api.post('/momo-transactions/collect/', data);
  },

  async disburseLoanMomo(data: {
    loan_id: string;
    phone_number: string;
    amount: string;
    provider_code: string;
  }) {
    return api.post('/momo-transactions/disburse/', data);
  },

  // Deposit Accounts
  async getDepositAccounts(params?: { client?: string; status?: string }) {
    try {
      const queryParams: Record<string, string> = {};
      if (params?.client) queryParams.client = params.client;
      if (params?.status) queryParams.status = params.status;
      return await api.get('/deposit-accounts/', queryParams);
    } catch (err) {
      console.warn('Failed to load deposit accounts', err);
      return null;
    }
  },

  async postDeposit(accountId: string, data: { amount: string; payment_method?: string; description?: string }) {
    return api.post(`/deposit-accounts/${accountId}/deposit/`, data);
  },

  async postWithdrawal(accountId: string, data: { amount: string; payment_method?: string; description?: string }) {
    return api.post(`/deposit-accounts/${accountId}/withdraw/`, data);
  },

  // Investors
  async getInvestors() {
    try {
      return await api.get('/investors/');
    } catch (err) {
      console.warn('Failed to load investors', err);
      return null;
    }
  },

  async getInvestorPortfolioSummary() {
    try {
      return await api.get('/investors/portfolio_summary/');
    } catch (err) {
      console.warn('Failed to load investor portfolio summary', err);
      return null;
    }
  },

  async createShareLink(investorId: string, daysValid: number = 30, maxViews?: number) {
    return api.post(`/investors/${investorId}/create_share_link/`, {
      days_valid: daysValid,
      max_views: maxViews,
    });
  },

  // Import
  async validateImport(importType: string, file: File): Promise<ImportJob | null> {
    try {
      const formData = new FormData();
      formData.append('import_type', importType);
      formData.append('file', file);

      const { data: sessionData } = await (await import('./supabase')).supabase.auth.getSession();
      const token = sessionData.session?.access_token || '';
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

      const res = await fetch(`${API_BASE}/import-jobs/validate/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    } catch (err) {
      console.warn('Failed to validate import', err);
      return null;
    }
  },

  async commitImport(jobId: string) {
    return api.post(`/import-jobs/${jobId}/commit/`, {});
  },

  // Compliance
  async getPrudentialReturns(params?: { status?: string }) {
    try {
      const queryParams: Record<string, string> = {};
      if (params?.status) queryParams.status = params.status;
      return await api.get('/prudential-returns/', queryParams);
    } catch (err) {
      console.warn('Failed to load prudential returns', err);
      return null;
    }
  },
};

export default apiService;
