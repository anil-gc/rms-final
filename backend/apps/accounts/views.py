from django.contrib.auth import logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.cache import patch_cache_control
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import STAFF_ROLES, User
from .permissions import HasRole, IsOwner, IsProvisionedUser
from .serializers import (
    OwnerLoginSerializer,
    OwnerPasswordChangeSerializer,
    PINChangeSerializer,
    PINResetSerializer,
    StaffCreateSerializer,
    StaffLoginSerializer,
    StaffStateSerializer,
    UserSerializer,
)


def csrf_failure(request, reason=""):
    response = JsonResponse({"detail": "CSRF validation failed."}, status=403)
    patch_cache_control(response, no_store=True)
    return response


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(sensitive_post_parameters(), name="dispatch")
class AccountAPIView(APIView):
    """Explicit CSRF protection also covers anonymous login requests."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True)
        return response


class CSRFView(AccountAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


class OwnerLoginView(AccountAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = OwnerLoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.verify_credentials(
            request,
            data.validated_data["username"],
            data.validated_data["password"],
            kind="password",
        )
        if user.role != User.Role.OWNER:
            raise services.InvalidCredentials()
        services.start_session(request, user)
        return Response({"user": UserSerializer(user).data, "csrf_token": get_token(request)})


class StaffLoginView(AccountAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        data = StaffLoginSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.verify_credentials(
            request, data.validated_data["username"], data.validated_data["pin"], kind="pin"
        )
        if user.role not in STAFF_ROLES:
            raise services.InvalidCredentials()
        services.start_session(request, user)
        return Response({"user": UserSerializer(user).data, "csrf_token": get_token(request)})


class MeView(AccountAPIView):
    permission_classes = [IsProvisionedUser]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(AccountAPIView):
    permission_classes = [IsProvisionedUser]

    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CanChangePIN(HasRole):
    allowed_roles = STAFF_ROLES

    def has_permission(self, request, view):
        # Temporary-PIN sessions can change their PIN before accessing other APIs.
        return (
            IsProvisionedUser().has_permission(request, view) and request.user.role in STAFF_ROLES
        )


class PINChangeView(AccountAPIView):
    permission_classes = [CanChangePIN]

    def post(self, request):
        data = PINChangeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.change_pin(request, **data.validated_data)
        return Response(UserSerializer(user).data)


class OwnerPasswordChangeView(AccountAPIView):
    permission_classes = [IsOwner]

    def post(self, request):
        data = OwnerPasswordChangeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.change_owner_password(request, **data.validated_data)
        return Response(UserSerializer(user).data)


class StaffListCreateView(AccountAPIView):
    permission_classes = [IsOwner]

    def get(self, request):
        users = User.objects.filter(role__in=STAFF_ROLES).order_by("username")
        return Response(UserSerializer(users, many=True).data)

    def post(self, request):
        data = StaffCreateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.create_staff(request, **data.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class StaffStateView(AccountAPIView):
    permission_classes = [IsOwner]

    def patch(self, request, pk):
        data = StaffStateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.change_staff_state(request, pk, **data.validated_data)
        return Response(UserSerializer(user).data)


class StaffPINResetView(AccountAPIView):
    permission_classes = [IsOwner]

    def post(self, request, pk):
        data = PINResetSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.reset_staff_pin(request, pk, **data.validated_data)
        return Response(UserSerializer(user).data)
