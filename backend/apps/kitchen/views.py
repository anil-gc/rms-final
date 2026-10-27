from django.utils.cache import patch_cache_control
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole, IsChef, IsWaiter
from apps.orders.services import approved_lines

from .serializers import EmptyInputSerializer, KitchenTicketSerializer
from .services import mark_preparing, mark_ready, mark_served


class CanReadKitchen(HasRole):
    allowed_roles = ("chef", "waiter", "manager", "owner")


class KitchenAPI(APIView):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True)
        return response


class KitchenTicketList(KitchenAPI, generics.ListAPIView):
    permission_classes = [CanReadKitchen]
    serializer_class = KitchenTicketSerializer

    def get_queryset(self):
        # Base queryset: all approved order lines for open sessions
        lines = (
            approved_lines()
            .select_related("batch__order__session__table", "batch__submitted_by", "kitchen_ticket")
            .order_by("batch__reviewed_at", "id")
        )

        status_filter = self.request.query_params.get("status")
        if status_filter:
            if status_filter not in ["pending", "preparing", "ready", "served"]:
                raise ValidationError({"detail": "Invalid status filter."})

            if status_filter == "pending":
                # Pending means NO kitchen_ticket OR status="pending" (if explicit)
                lines = lines.filter(kitchen_ticket__isnull=True)
            else:
                lines = lines.filter(kitchen_ticket__status=status_filter)

        return lines


class MarkPreparing(KitchenAPI):
    permission_classes = [IsChef]

    def post(self, request, line_id):
        serializer = EmptyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket, created = mark_preparing(order_line_id=line_id, actor=request.user)
        # Fetch the complete line with relationships
        line = (
            approved_lines()
            .select_related("batch__order__session__table", "batch__submitted_by", "kitchen_ticket")
            .get(pk=line_id)
        )
        return Response(KitchenTicketSerializer(line).data, status=200)


class MarkReady(KitchenAPI):
    permission_classes = [IsChef]

    def post(self, request, line_id):
        serializer = EmptyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket, updated = mark_ready(order_line_id=line_id, actor=request.user)
        line = (
            approved_lines()
            .select_related("batch__order__session__table", "batch__submitted_by", "kitchen_ticket")
            .get(pk=line_id)
        )
        return Response(KitchenTicketSerializer(line).data, status=200)


class MarkServed(KitchenAPI):
    permission_classes = [IsWaiter]

    def post(self, request, line_id):
        serializer = EmptyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket, updated = mark_served(order_line_id=line_id, actor=request.user)
        line = (
            approved_lines()
            .select_related("batch__order__session__table", "batch__submitted_by", "kitchen_ticket")
            .get(pk=line_id)
        )
        return Response(KitchenTicketSerializer(line).data, status=200)
