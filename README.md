# Pan-African Microfinance SaaS Platform

Multi-tenant microfinance management system built for Ghana and Zambia, deployable across Sub-Saharan Africa. Supports credit-only and deposit-taking institutions across all regulatory tiers.

---

## 🚀 Deployment Status

| Service | Platform | URL | Status |
|---|---|---|---|
| **Next.js Frontend** | Railway (`zealous-gentleness`) | https://pan-african-mfi-production.up.railway.app | ✅ Online |
| **Django Backend API** | Railway (`pan-african-mfi`) | https://pan-african-mfi-production.up.railway.app/api/v1 | ✅ Online |
| **Database + Auth** | Supabase (`gdskcpfwhzjnmaktemjk`) | https://gdskcpfwhzjnmaktemjk.supabase.co | ✅ Active |
| **Redis / Celery** | Railway (shared) | `REDIS_URL` injected by Railway | ✅ Online |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Browser / Mobile)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
         ┌────────────▼────────────┐
         │  Next.js 14 PWA         │  Railway: zealous-gentleness
         │  /mfi-frontend          │  Standalone output, offline-capable
         │  Tailwind CSS           │
         └────────────┬────────────┘
                      │ REST (JWT)
         ┌────────────▼────────────┐
         │  Django 5 + DRF         │  Railway: pan-african-mfi
         │  /apps  /config         │  Gunicorn, 2 workers
         │  Celery Beat (tasks)    │  + Redis for task queue
         └────────────┬────────────┘
                      │ psycopg2 + Supabase SDK
         ┌────────────▼────────────┐
         │  Supabase (PostgreSQL)  │  Project: Pan-African MFI
         │  59 tables (public+     │  Region: eu-west-1
         │  audit schemas)         │  RLS on all tenant tables
         │  Supabase Auth          │
         │  Supabase Storage       │
         └─────────────────────────┘
```

---

## ✅ What Has Been Built & Deployed

### Database — Supabase (ALL DONE — do not re-run migrations)

All 7 migration files have been applied to Supabase project `gdskcpfwhzjnmaktemjk`. The schema is **complete and live**.

| Migration | Contents | Status |
|---|---|---|
| `001_core_schema.sql` | Extensions, audit schema, country_packs, licence_tiers, tenants, rule_set_versions, licence_profiles, branches | ✅ Applied |
| `002_auth_rbac.sql` | users, roles, permissions, role_permissions, user_roles, maker_checker_configs, approval_requests, approval_decisions, active_sessions, session_configs, ip_whitelists | ✅ Applied |
| `003_clients_kyc.sql` | clients, groups, group_members, kyc_documents, credit_score_models, client_credit_scores | ✅ Applied |
| `004_loans_deposits.sql` | loan_products, loans, repayment_schedules, repayments, deposit_products, deposit_accounts, deposit_transactions | ✅ Applied |
| `005_remaining_tables.sql` | gl_accounts, accounting_periods, gl_transactions, gl_entries, exchange_rates, aml_alerts, strs, transaction_monitoring_rules, prudential_returns, investor_profiles, investor_share_links, dividends, mobile_money_providers, mobile_money_transactions, mobile_money_reconciliation, notification_rules, notifications, sms_templates, sms_log, ussd_sessions, report_definitions, report_schedules, report_runs, onboarding_progress, import_jobs, api_keys, webhooks, webhook_deliveries, sync_queue, audit.logs, audit.login_attempts | ✅ Applied |
| `006_rls_triggers.sql` | Row-level security on all 49 tenant-scoped tables + 6 business logic triggers (deposit permission, GL balance, maker-checker, KYC gate, test data block, audit log) + auto `updated_at` trigger | ✅ Applied |
| `007_seed_data.sql` | Ghana + Zambia country packs, 7 licence tiers, 6 rule set versions, 6 mobile money providers (MTN/Vodafone/AirtelTigo GH, MTN/Airtel/Zoona ZM), 17 SMS templates, 42 permissions, 20 report definitions | ✅ Applied |

**Total: 59 tables (57 public + 2 audit), RLS on all tenant tables, full seed data.**

---

### Django Backend — `/` root (ALL DONE)

| App | Description |
|---|---|
| `apps/accounts` | Custom auth, JWT middleware, session management |
| `apps/tenants` | Multi-tenancy, country pack engine, licence tier logic |
| `apps/clients` | Client CRUD, KYC verification, offline sync |
| `apps/loans` | Loan lifecycle, repayment schedules, PAR calculation |
| `apps/deposits` | Deposit accounts and transactions (feature-flagged) |
| `apps/ledger` | General ledger, double-entry, period close |
| `apps/compliance` | AML alerts, STR filing, prudential returns |
| `apps/investors` | Investor profiles, dividends, share links |
| `apps/mobile_money` | Provider-agnostic MoMo disbursement/collection |
| `apps/scoring` | Credit scoring engine with configurable criteria |
| `apps/reports` | PDF/Excel report generation (WeasyPrint + openpyxl) |
| `apps/notifications` | In-app alerts + SMS via Africa's Talking |
| `apps/onboarding` | Onboarding wizard, bulk data import engine |
| `apps/integrations` | API keys, webhooks, webhook delivery log |
| `apps/audit` | Immutable audit log (append-only) |
| `config/` | Django settings, WSGI, Celery config, URL routing |

**Key files:**
- `config/settings.py` — all env vars via `os.environ.get()`
- `apps/api_views.py` — main DRF API views
- `apps/api_urls.py` — URL routing for `/api/v1/`
- `apps/api_serializers.py` — DRF serializers
- `apps/tasks.py` — Celery tasks (SMS reminders, report scheduling, PAR calc)
- `Dockerfile` — Python 3.12, gunicorn, WeasyPrint system deps

---

### Next.js Frontend — `/mfi-frontend` (ALL DONE)

| Dashboard | Role | File |
|---|---|---|
| CEO/CFO Dashboard | `CEO_CFO` | `src/app/dashboard/page.tsx` |
| Accountant Dashboard | `ACCOUNTANT` | `src/components/dashboards/AccountantDashboard.tsx` |
| Board Director Dashboard | `BOARD_DIRECTOR` | `src/components/dashboards/BoardDashboard.tsx` |
| Compliance Dashboard | `COMPLIANCE_OFFICER` | `src/components/dashboards/ComplianceDashboard.tsx` |
| Credit Manager Dashboard | `CREDIT_MANAGER` | `src/components/dashboards/CreditManagerDashboard.tsx` |
| Loan Officer Dashboard | `LOAN_OFFICER` | `src/components/dashboards/LoanOfficerDashboard.tsx` |
| Security Admin Dashboard | `IT_SECURITY_ADMIN` | `src/components/dashboards/SecurityAdminDashboard.tsx` |
| Investor Share Page | Public (token-gated) | `src/app/share/page.tsx` |
| Login | All | `src/app/login/page.tsx` |
| Client Management | All | `src/app/clients/page.tsx` |
| Onboarding Wizard | Admin | `src/app/onboarding/page.tsx` |

**Key files:**
- `src/lib/supabase.ts` — Supabase client + Django API client
- `src/stores/index.ts` — Zustand state management
- `src/types/index.ts` — TypeScript types for all 57 tables
- `src/lib/offline-store.ts` — IndexedDB offline sync store
- `next.config.js` — standalone output, security headers

---

## 🔑 Environment Variables

### Railway: `pan-african-mfi` (Django backend) — ALL SET ✅

```
DJANGO_SECRET_KEY          — Django secret (set in Railway)
DJANGO_DEBUG               — False
ENVIRONMENT                — production
ALLOWED_HOSTS              — pan-african-mfi-production.up.railway.app,localhost,127.0.0.1
DB_HOST                    — db.gdskcpfwhzjnmaktemjk.supabase.co
DB_NAME                    — postgres
DB_USER                    — postgres
DB_PORT                    — 5432
DB_PASSWORD                — set in Railway (Supabase DB password)
SUPABASE_URL               — https://gdskcpfwhzjnmaktemjk.supabase.co
SUPABASE_ANON_KEY          — set in Railway
SUPABASE_SERVICE_ROLE_KEY  — set in Railway
CORS_ALLOWED_ORIGINS       — https://pan-african-mfi-production.up.railway.app
REDIS_URL                  — injected automatically by Railway Redis service
NEXT_PUBLIC_API_URL        — https://pan-african-mfi-production.up.railway.app/api/v1
NEXT_PUBLIC_SUPABASE_URL   — https://gdskcpfwhzjnmaktemjk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY — set in Railway
```

### Railway: `zealous-gentleness` (Next.js frontend) — ALL SET ✅

```
NEXT_PUBLIC_SUPABASE_URL      — https://gdskcpfwhzjnmaktemjk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY — set in Railway
NEXT_PUBLIC_API_URL           — https://pan-african-mfi-production.up.railway.app/api/v1
```

### Optional (not yet configured)
```
AFRICAS_TALKING_API_KEY    — for live SMS (Africa's Talking production key)
AFRICAS_TALKING_USERNAME   — Africa's Talking username
RESEND_API_KEY             — for transactional email
```

---

## 🛠️ Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL (or use the Supabase connection directly)
- Redis

### Backend

```bash
# Clone and set up Python env
git clone https://github.com/kfrem/pan-african-mfi.git
cd pan-african-mfi
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create a .env file (never commit this)
cp .env.example .env   # then fill in values

# Run Django
python manage.py runserver
```

### Frontend

```bash
cd mfi-frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`, backend on `http://localhost:8000`.

---

## 📁 Repository Structure

```
pan-african-mfi/
├── apps/                        # Django apps (one per domain)
│   ├── accounts/                # Auth, sessions, middleware
│   ├── tenants/                 # Multi-tenancy, country packs
│   ├── clients/                 # Client management + KYC
│   ├── loans/                   # Loan lifecycle
│   ├── deposits/                # Deposit management
│   ├── ledger/                  # General ledger
│   ├── compliance/              # AML, STR, prudential returns
│   ├── investors/               # Investor portal
│   ├── mobile_money/            # MoMo integration
│   ├── scoring/                 # Credit scoring engine
│   ├── reports/                 # Report generation
│   ├── notifications/           # Alerts + SMS
│   ├── onboarding/              # Setup wizard + data import
│   ├── integrations/            # API keys + webhooks
│   ├── audit/                   # Immutable audit log
│   ├── api_views.py             # Main API views
│   ├── api_urls.py              # API URL routing
│   ├── api_serializers.py       # DRF serializers
│   └── tasks.py                 # Celery background tasks
├── config/                      # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── celery.py
├── mfi-frontend/                # Next.js 14 PWA
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # Role-based dashboards
│   │   ├── lib/                 # Supabase + API client
│   │   ├── stores/              # Zustand state
│   │   └── types/               # TypeScript types
│   ├── package.json
│   └── next.config.js
├── supabase/
│   └── migrations/              # All 7 SQL migrations (ALREADY APPLIED)
│       ├── 001_core_schema.sql
│       ├── 002_auth_rbac.sql
│       ├── 003_clients_kyc.sql
│       ├── 004_loans_deposits.sql
│       ├── 005_remaining_tables.sql
│       ├── 006_rls_triggers.sql
│       └── 007_seed_data.sql
├── templates/                   # Django HTML report templates
├── database_schema_v3_FINAL.md  # Full schema specification
├── Dockerfile                   # Django backend container
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

---

## 🔄 Git Commit History (Key Milestones)

| Commit | Description |
|---|---|
| `fdd04e2` | Fix Dockerfile by removing duplicate package entry |
| `b53d229` | Update AccountantDashboard.tsx |
| `fe76c1d` | Fix typo in import statement for TrendingUp icon |
| `e1a262e` | Fix missing Eye icon import in AccountantDashboard |
| `4dbf360` | Fix /share page: wrap useSearchParams in Suspense for Next.js static export |

---

## 🗺️ What's Next

- [ ] Wire up Django API endpoints to live Supabase data (currently returns mock/empty responses)
- [ ] Implement Supabase Auth flow in the frontend login page
- [ ] Add Africa's Talking credentials for live SMS
- [ ] Add Resend API key for transactional email
- [ ] Run Django migrations (`python manage.py migrate`) against Supabase DB
- [ ] Implement the onboarding wizard flow end-to-end
- [ ] Set up Celery Beat schedule for PAR recalculation and SMS reminders
- [ ] Add remaining country packs (Nigeria, Kenya, Uganda)

---

## 🌍 Country Support

| Country | Regulator | Currency | Tiers | MoMo Providers |
|---|---|---|---|---|
| **Ghana** | Bank of Ghana (BoG) | GHS | Tier 1–4 | MTN MoMo, Vodafone Cash, AirtelTigo |
| **Zambia** | Bank of Zambia (BoZ) | ZMW | Tier I–III | MTN MoMo, Airtel Money, Zoona |

---

*Pan-African Microfinance SaaS Platform — v3.0*
