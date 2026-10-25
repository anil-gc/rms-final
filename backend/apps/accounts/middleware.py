from django.http import JsonResponse
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.deprecation import MiddlewareMixin

from .rate_limits import (
    LoginRateLimited,
    consume_credential_attempt,
    refund_successful_account_attempt,
)


class AdminCredentialRateLimitMiddleware(MiddlewareMixin):
    """Admin's password form checks passwords directly, bypassing authenticate()."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if (
            request.method == "POST"
            and request.resolver_match.view_name == "admin:password_change"
            and request.user.is_authenticated
            and request.user.is_active
        ):
            try:
                request._rms_admin_password_budget = consume_credential_attempt(
                    request.user.username, request.META.get("REMOTE_ADDR", "unknown")
                )
            except LoginRateLimited as error:
                response = JsonResponse(
                    {"detail": "Too many attempts. Try again later."}, status=429
                )
                response["Retry-After"] = str(error.wait)
                patch_cache_control(response, no_store=True)
                return response
        return None

    def process_response(self, request, response):
        reservation = getattr(request, "_rms_admin_password_budget", None)
        if (
            reservation
            and response.status_code == 302
            and response.get("Location") == reverse("admin:password_change_done")
        ):
            refund_successful_account_attempt(reservation)
        return response
