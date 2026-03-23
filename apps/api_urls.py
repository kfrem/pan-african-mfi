"""
API URL routing — Pan-African Microfinance SaaS
All endpoints under /api/v1/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notifications.ussd_handler import ussd_callback
from apps.api_views import (
    CountryPackViewSet, LicenceTierViewSet,
    TenantViewSet, BranchViewSet,
    UserViewSet, RoleViewSet,
    ClientViewSet, GroupViewSet, KycDocumentViewSet,
    LoanProductViewSet, LoanViewSet, RepaymentViewSet,
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

urlpatterns = [
    path('', include(router.urls)),
    # USSD callback (Africa's Talking)
    path('ussd/callback', ussd_callback, name='ussd-callback'),
]

# ─── ENDPOINT SUMMARY ───
#
# GET    /api/v1/countries/                 List available countries
# GET    /api/v1/licence-tiers/             List licence tiers (filter: ?country=GH)
# GET    /api/v1/tenants/                   Get current tenant
# PATCH  /api/v1/tenants/{id}/              Update tenant settings (branding, etc)
# CRUD   /api/v1/branches/                  Branch management
# GET    /api/v1/users/me/                  Current user profile
# CRUD   /api/v1/users/                     User management
# GET    /api/v1/roles/                     List roles
# CRUD   /api/v1/clients/                   Client management (filter: ?branch=, ?kyc_status=, ?search=)
# POST   /api/v1/clients/{id}/verify_kyc/   Verify client KYC
# POST   /api/v1/clients/sync_batch/        Sync offline-created clients
# CRUD   /api/v1/groups/                    Group management
# CRUD   /api/v1/kyc-documents/             KYC document management
# CRUD   /api/v1/loan-products/             Loan product configuration
# GET    /api/v1/loans/                     List loans (filter: ?status=, ?client=, ?branch=)
# POST   /api/v1/loans/apply/               Submit loan application
# POST   /api/v1/loans/{id}/approve/        Approve loan (checker)
# POST   /api/v1/loans/{id}/disburse/       Disburse approved loan
# GET    /api/v1/loans/dashboard_stats/     Portfolio summary statistics
# GET    /api/v1/repayments/                List repayments (filter: ?loan=)
# POST   /api/v1/repayments/capture/        Capture repayment (offline-capable)
