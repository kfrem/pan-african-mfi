"""
Core middleware for tenant isolation and audit logging.
These run on EVERY request to enforce multi-tenancy and security.
"""
import jwt
import logging
from django.conf import settings
from django.db import connection
from rest_framework import authentication, exceptions

logger = logging.getLogger(__name__)


class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """
    Authenticate requests using Supabase JWT tokens.
    Extracts user_id and tenant_id from the JWT claims.
    """

    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return None

        token = auth_header[7:]
        try:
            # Supabase JWTs are signed with the JWT secret from project settings
            payload = jwt.decode(
                token,
                settings.SUPABASE_ANON_KEY,  # Use JWT secret in production
                algorithms=['HS256'],
                audience='authenticated',
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('Invalid token')

        user_id = payload.get('sub')
        tenant_id = payload.get('tenant_id')

        if not user_id:
            raise exceptions.AuthenticationFailed('Token missing user identity')

        # Attach tenant_id to request for middleware use
        request.supabase_user_id = user_id
        request.tenant_id = tenant_id

        # Return a lightweight user object — full User model loaded by TenantMiddleware
        return (payload, token)


class TenantMiddleware:
    """
    Sets the PostgreSQL session variable for RLS enforcement.
    Every database query in this request will be filtered by tenant_id.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = getattr(request, 'tenant_id', None)

        if tenant_id:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL app.current_tenant = %s", [str(tenant_id)])
                cursor.execute("SET LOCAL app.current_user_id = %s",
                             [str(getattr(request, 'supabase_user_id', ''))])

        response = self.get_response(request)
        return response


class AuditMiddleware:
    """
    Captures request metadata for audit logging.
    Individual model saves trigger audit log entries via signals.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Store request metadata for audit signal handlers to use
        request.audit_ip = self._get_client_ip(request)
        request.audit_user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        response = self.get_response(request)
        return response

    @staticmethod
    def _get_client_ip(request):
        """Extract real client IP, respecting proxy headers."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
