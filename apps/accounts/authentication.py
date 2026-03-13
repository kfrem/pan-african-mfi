# Re-export from middleware for clean imports
from apps.accounts.middleware import SupabaseJWTAuthentication

__all__ = ['SupabaseJWTAuthentication']
