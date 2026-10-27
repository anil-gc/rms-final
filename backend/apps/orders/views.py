from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils.cache import patch_cache_control
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole, IsCashier, IsWaiter
from apps.restaurants.models import DiningTable

from .models import Order, OrderBatch, OrderEvent
from .serializers import (
    BatchSerializer,
    EmptyInputSerializer,
    OrderDetailSerializer,
    OrderSummarySerializer,
    RejectionSerializer,
    SubmissionSerializer,
)
from .services import open_session, review_batch, submit_batch


class CanReadOrders(HasRole):
    allowed_roles = ("waiter", "cashier", "owner", "manager")


class OrderAPI(APIView):
    permission_classes = [CanReadOrders]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        patch_cache_control(response, no_store=True)
        return response


def batches():
    return OrderBatch.objects.select_related(
        "submitted_by", "reviewed_by", "order__session__table"
    ).prefetch_related("lines")


def orders():
    return Order.objects.select_related("session__table").prefetch_related(
        Prefetch("batches", queryset=batches()),
        Prefetch("events", queryset=OrderEvent.objects.select_related("actor")),
    )


class OrderPagination(PageNumberPagination):
    page_size = 20


class OrderList(OrderAPI, generics.ListAPIView):
    serializer_class = OrderSummarySerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        return Order.objects.filter(session__state="open").select_related("session__table")


class OrderDetail(OrderAPI, generics.RetrieveAPIView):
    serializer_class = OrderDetailSerializer

    def get_queryset(self):
        return orders()


class ActiveTableOrder(OrderAPI):
    def get(self, request, table_id):
        table = get_object_or_404(DiningTable, pk=table_id)
        order = orders().filter(session__table=table, session__state="open").first()
        return Response({"order": OrderDetailSerializer(order).data if order else None})


class OpenTableOrder(OrderAPI):
    permission_classes = [IsWaiter]

    def post(self, request, table_id):
        serializer = EmptyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, created = open_session(table_id=table_id, actor=request.user)
        return Response(
            OrderDetailSerializer(orders().get(pk=order.pk)).data, status=201 if created else 200
        )


class SubmitBatch(OrderAPI):
    permission_classes = [IsWaiter]

    def post(self, request, pk):
        serializer = SubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch, created = submit_batch(order_id=pk, actor=request.user, **serializer.validated_data)
        return Response(
            BatchSerializer(batches().get(pk=batch.pk)).data, status=201 if created else 200
        )


class BatchList(OrderAPI, generics.ListAPIView):
    serializer_class = BatchSerializer
    pagination_class = OrderPagination

    def get_queryset(self):
        status = self.request.query_params.get("status", "pending")
        if status not in {"all", *OrderBatch.Status.values}:
            raise ValidationError({"detail": "Choose pending, approved, rejected or all."})
        query = batches().order_by("-submitted_at", "-id")
        return query if status == "all" else query.filter(status=status)


class BatchDetail(OrderAPI, generics.RetrieveAPIView):
    serializer_class = BatchSerializer

    def get_queryset(self):
        return batches()


class ReviewBatch(OrderAPI):
    permission_classes = [IsCashier]
    decision = "approved"

    def post(self, request, pk):
        serializer = (RejectionSerializer if self.decision == "rejected" else EmptyInputSerializer)(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        batch = review_batch(
            batch_id=pk, actor=request.user, decision=self.decision, **serializer.validated_data
        )
        return Response(BatchSerializer(batches().get(pk=batch.pk)).data)


class RejectBatch(ReviewBatch):
    decision = "rejected"
