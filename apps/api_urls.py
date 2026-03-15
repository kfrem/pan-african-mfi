"""
API URL routing — Pan-African Microfinance SaaS
All endpoints under /api/v1/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.api_views import (
    CountryPackViewSet, LicenceTierViewSet,
    TenantViewSet, BranchViewSet,
    UserViewSet, RoleViewSet,
    ClientViewSet, GroupViewSet, KycDocumentViewSet,
    LoanProductViewSet, LoanViewSet, RepaymentViewSet,
    DepositProductViewSet, DepositAccountViewSet, DepositTransactionViewSet,
    InvestorProfileViewSet, InvestorShareLinkViewSet,
    AmlAlertViewSet, PrudentialReturnViewSet,
    MobileMoneyProviderViewSet, MobileMoneyTransactionViewSet,
    ReportDefinitionViewSet, ReportRunViewSet,
    ImportJobViewSet,
)

router = DefaultRouter()

# Reference data
router.register(r'countries', CountryPackViewSet, basename='countries')
router.register(r'licence-tiers', LicenceTierViewSet, basename='licence-tiers')

# Tenant management
router.register(r'tenants', TenantViewSet, basename='tenants')
router.register(r'branches', BranchViewSet, basename='branches')

# Users & RBAC
router.register(r'users', UserViewSet, basename='users')
router.register(r'roles', RoleViewSet, basename='roles')

# Clients & KYC
router.register(r'clients', ClientViewSet, basename='clients')
router.register(r'groups', GroupViewSet, basename='groups')
router.register(r'kyc-documents', KycDocumentViewSet, basename='kyc-documents')

# Loans & Repayments
router.register(r'loan-products', LoanProductViewSet, basename='loan-products')
router.register(r'loans', LoanViewSet, basename='loans')
router.register(r'repayments', RepaymentViewSet, basename='repayments')

# Deposits
router.register(r'deposit-products', DepositProductViewSet, basename='deposit-products')
router.register(r'deposit-accounts', DepositAccountViewSet, basename='deposit-accounts')
router.register(r'deposit-transactions', DepositTransactionViewSet, basename='deposit-transactions')

# Investors
router.register(r'investors', InvestorProfileViewSet, basename='investors')
router.register(r'investor-share-links', InvestorShareLinkViewSet, basename='investor-share-links')

# Compliance
router.register(r'aml-alerts', AmlAlertViewSet, basename='aml-alerts')
router.register(r'prudential-returns', PrudentialReturnViewSet, basename='prudential-returns')

# Mobile Money
router.register(r'momo-providers', MobileMoneyProviderViewSet, basename='momo-providers')
router.register(r'momo-transactions', MobileMoneyTransactionViewSet, basename='momo-transactions')

# Reports
router.register(r'report-definitions', ReportDefinitionViewSet, basename='report-definitions')
router.register(r'report-runs', ReportRunViewSet, basename='report-runs')

# Onboarding / Import
router.register(r'import-jobs', ImportJobViewSet, basename='import-jobs')

urlpatterns = [
    path('', include(router.urls)),
    # USSD callback (Africa's Talking)
    path('ussd/callback', 'apps.notifications.ussd_handler.ussd_callback', name='ussd-callback'),
]

# ─── ENDPOINT SUMMARY ───
#
# GET    /api/v1/countries/                         List available countries
# GET    /api/v1/licence-tiers/                     List licence tiers (filter: ?country=GH)
# GET    /api/v1/tenants/                           Get current tenant
# PATCH  /api/v1/tenants/{id}/                      Update tenant settings
# CRUD   /api/v1/branches/                          Branch management
# GET    /api/v1/users/me/                          Current user profile
# CRUD   /api/v1/users/                             User management
# GET    /api/v1/roles/                             List roles
# CRUD   /api/v1/clients/                           Client management
# POST   /api/v1/clients/{id}/verify_kyc/           Verify client KYC
# POST   /api/v1/clients/sync_batch/                Sync offline-created clients
# CRUD   /api/v1/groups/                            Group management
# CRUD   /api/v1/kyc-documents/                     KYC document management
# CRUD   /api/v1/loan-products/                     Loan product configuration
# GET    /api/v1/loans/                             List loans
# POST   /api/v1/loans/apply/                       Submit loan application
# POST   /api/v1/loans/{id}/approve/                Approve loan (checker)
# POST   /api/v1/loans/{id}/disburse/               Disburse approved loan
# GET    /api/v1/loans/dashboard_stats/             Portfolio summary statistics
# GET    /api/v1/repayments/                        List repayments
# POST   /api/v1/repayments/capture/                Capture repayment (offline-capable)
# CRUD   /api/v1/deposit-products/                  Deposit product configuration
# CRUD   /api/v1/deposit-accounts/                  Deposit account management
# POST   /api/v1/deposit-accounts/{id}/deposit/     Post a deposit transaction
# POST   /api/v1/deposit-accounts/{id}/withdraw/    Post a withdrawal transaction
# GET    /api/v1/deposit-transactions/              List deposit transactions
# CRUD   /api/v1/investors/                         Investor profile management
# POST   /api/v1/investors/{id}/create_share_link/  Generate shareable investor link
# GET    /api/v1/investors/portfolio_summary/       Aggregate portfolio view
# GET    /api/v1/investor-share-links/              List active share links
# CRUD   /api/v1/aml-alerts/                        AML alert management
# POST   /api/v1/aml-alerts/{id}/assign/            Assign alert to officer
# POST   /api/v1/aml-alerts/{id}/close/             Close alert with no action
# CRUD   /api/v1/prudential-returns/                Prudential returns management
# POST   /api/v1/prudential-returns/{id}/submit/    Submit a prudential return
# GET    /api/v1/momo-providers/                    List mobile money providers
# GET    /api/v1/momo-transactions/                 List mobile money transactions
# POST   /api/v1/momo-transactions/collect/         Initiate collection for loan repayment
# POST   /api/v1/momo-transactions/disburse/        Initiate loan disbursement
# POST   /api/v1/momo-transactions/{id}/callback/   Handle provider webhook
# GET    /api/v1/report-definitions/                List available report definitions
# GET    /api/v1/report-runs/                       List report generation runs
# POST   /api/v1/report-runs/request_report/        Queue ad-hoc report generation
# GET    /api/v1/import-jobs/                       List import jobs
# POST   /api/v1/import-jobs/validate/              Upload and validate import file
# POST   /api/v1/import-jobs/{id}/commit/           Commit a validated import
