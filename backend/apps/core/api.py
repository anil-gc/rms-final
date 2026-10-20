"""Shared HTTP behavior for the authenticated workspace APIs."""

from django.db import IntegrityError, transaction
from django.utils.cache import patch_cache_control
from rest_framework import mixins, serializers, viewsets
from rest_framework.permissions import SAFE_METHODS
from rest_framework.views import APIView

from apps.accounts.permissions import IsAuthenticatedAndPinReady, IsOwnerOrManager


class StrictModelSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            writable = {name for name, field in self.fields.items() if not field.read_only}
            unknown = set(data.keys()) - writable
            if unknown:
                raise serializers.ValidationError(
                    {name: "Unknown or read-only field." for name in sorted(unknown)}
                )
        return super().to_internal_value(data)


class WorkspaceAccessMixin:
    def get_permissions(self):
        permission = (
            IsAuthenticatedAndPinReady if self.request.method in SAFE_METHODS else IsOwnerOrManager
        )
        return [permission()]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True)
        return response


class WorkspaceAPIView(WorkspaceAccessMixin, APIView):
    pass


class WorkspaceModelViewSet(
    WorkspaceAccessMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Archive via PATCH; expose neither hard deletion nor full replacement."""

    http_method_names = ["get", "post", "patch", "head", "options"]

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError as error:
            raise serializers.ValidationError(
                {
                    "detail": "The name is already in use or related data changed. "
                    "Refresh and try again."
                }
            ) from error

    def partial_update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().partial_update(request, *args, **kwargs)
        except IntegrityError as error:
            raise serializers.ValidationError(
                {"detail": "The record conflicts with existing data. Refresh and try again."}
            ) from error

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method == "PATCH":
            queryset = queryset.select_for_update()
        return queryset


def can_manage(user):
    return user.role in {"owner", "manager"}
