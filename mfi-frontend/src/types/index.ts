// ─── Core Types ───
export type UUID = string;

export interface Tenant {
  id: UUID;
  name: string;
  trading_name: string;
  country_code: string;
  country_name: string;
  licence_tier_id: UUID;
  licence_tier_name: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'TERMINATED';
  default_currency: string;
  default_language: string;
  timezone: string;
  logo_url: string;
  primary_brand_colour: string;
  secondary_brand_colour: string;
  custom_domain: string;
  tagline: string;
}

export interface User {
  id: UUID;
  auth_user_id: UUID;
  email: string;
  full_name: string;
  phone: string;
  branch_id: UUID | null;
  branch_name: string;
  is_active: boolean;
  mfa_enabled: boolean;
  language_preference: string;
  theme_preference: string;
  roles: string[];
  last_login_at: string | null;
}

export interface Branch {
  id: UUID;
  branch_code: string;
  branch_name: string;
  branch_type: 'URBAN' | 'PERI_URBAN' | 'RURAL';
  is_active: boolean;
}

// ─── Client Types ───
export interface Client {
  id: UUID;
  client_number: string;
  full_legal_name: string;
  first_name: string;
  last_name: string;
  client_type: 'INDIVIDUAL' | 'SME' | 'GROUP';
  date_of_birth: string | null;
  gender: string;
  national_id_type: string;
  national_id_number: string;
  phone_primary: string;
  email: string;
  city: string;
  region: string;
  occupation: string;
  monthly_income: number | null;
  risk_rating: 'LOW' | 'MEDIUM' | 'HIGH';
  is_pep: boolean;
  is_insider: boolean;
  kyc_status: 'INCOMPLETE' | 'COMPLETE' | 'VERIFIED' | 'EXPIRED';
  assigned_officer_id: UUID | null;
  officer_name: string;
  branch_id: UUID;
  branch_name: string;
  active_loans_count: number;
  total_exposure: string;
  created_at: string;
}

export interface ClientListItem {
  id: UUID;
  client_number: string;
  full_legal_name: string;
  client_type: string;
  phone_primary: string;
  kyc_status: string;
  risk_rating: string;
  branch_name: string;
  officer_name: string;
  is_insider: boolean;
  is_pep: boolean;
  created_at: string;
}

// ─── Loan Types ───
export interface LoanProduct {
  id: UUID;
  product_code: string;
  product_name: string;
  product_type: string;
  min_amount: number;
  max_amount: number;
  min_term_months: number;
  max_term_months: number;
  interest_method: 'FLAT' | 'REDUCING_BALANCE';
  default_interest_rate_pct: number;
  origination_fee_pct: number;
  requires_collateral: boolean;
  group_liability_type: string;
  allowed_frequencies: string[];
  is_active: boolean;
}

export interface Loan {
  id: UUID;
  loan_number: string;
  client_id: UUID;
  client_name: string;
  product_id: UUID;
  product_name: string;
  principal_amount: number;
  currency: string;
  interest_rate_pct: number;
  interest_method: string;
  term_months: number;
  repayment_frequency: string;
  total_repayable: number;
  outstanding_principal: number;
  arrears_amount: number;
  days_past_due: number;
  status: 'APPLICATION' | 'PENDING_APPROVAL' | 'APPROVED' | 'DISBURSED' | 'ACTIVE' | 'CLOSED' | 'WRITTEN_OFF';
  classification: 'CURRENT' | 'WATCH' | 'SUBSTANDARD' | 'DOUBTFUL' | 'LOSS';
  application_date: string;
  disbursement_date: string | null;
  maturity_date: string | null;
  loan_officer_id: UUID;
  officer_name: string;
  branch_name: string;
  is_insider_loan: boolean;
  override_flag: boolean;
}

export interface RepaymentScheduleItem {
  id: UUID;
  instalment_number: number;
  due_date: string;
  principal_due: number;
  interest_due: number;
  total_due: number;
  total_paid: number;
  balance_after: number;
  status: 'PENDING' | 'PAID' | 'PARTIAL' | 'OVERDUE';
  days_late: number;
}

export interface Repayment {
  id: UUID;
  loan_id: UUID;
  amount: number;
  currency: string;
  payment_method: 'CASH' | 'MOBILE_MONEY' | 'BANK_TRANSFER' | 'CHEQUE';
  payment_reference: string;
  received_at: string;
  receipt_number: string;
  received_by_name: string;
}

// ─── Dashboard Types ───
export interface PortfolioStats {
  total_portfolio: string;
  total_loans: number;
  total_arrears: string;
  par30_balance: string;
  par30_pct: number;
}

export interface CreditScore {
  id: UUID;
  total_score: number;
  risk_label: string;
  recommendation: string;
  component_scores: CreditScoreComponent[];
  computed_at: string;
}

export interface CreditScoreComponent {
  code: string;
  label: string;
  weight: number;
  raw_value: number | null;
  normalised_score: number;
  weighted_score: number;
}

export interface Notification {
  id: UUID;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  title: string;
  message: string;
  link: string;
  is_read: boolean;
  created_at: string;
}

export interface CovenantStatus {
  name: string;
  value: number;
  threshold: number;
  unit: string;
  status: 'pass' | 'watch' | 'breach';
}

// ─── Onboarding Types ───
export interface OnboardingStep {
  step: string;
  label: string;
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'SKIPPED';
  completed_at: string | null;
}

export interface OnboardingProgress {
  id: UUID;
  steps: OnboardingStep[];
  is_complete: boolean;
  load_demo_data: boolean;
}
