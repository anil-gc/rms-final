from decimal import Decimal

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsOwnerOrManager
from apps.inventory import services
from apps.inventory.models import InventoryItem, RecipeIngredient, StockMovement
from apps.inventory.serializers import (
    InventoryItemSerializer,
    RecipeIngredientSerializer,
    StockMovementSerializer,
)


class InventoryItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrManager]
    queryset = InventoryItem.objects.all().order_by("name")
    serializer_class = InventoryItemSerializer

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        try:
            quantity = Decimal(str(request.data.get("quantity", 0)))
            unit = request.data.get("unit")
            notes = request.data.get("notes", "")

            movement = services.receive_stock(
                item_id=pk,
                quantity=quantity,
                unit=unit,
                actor=request.user,
                notes=notes
            )
            return Response(StockMovementSerializer(movement).data, status=status.HTTP_200_OK)
        except (ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        try:
            new_quantity = Decimal(str(request.data.get("new_quantity", 0)))
            reason = request.data.get("reason", "")

            if not reason:
                return Response(
                    {"error": "Reason is mandatory for adjustments"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            movement = services.adjust_stock(
                item_id=pk,
                new_quantity=new_quantity,
                reason=reason,
                actor=request.user,
            )
            return Response(StockMovementSerializer(movement).data, status=status.HTTP_200_OK)
        except (ValueError, TypeError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsOwnerOrManager]
    queryset = StockMovement.objects.all().select_related("item", "actor")
    serializer_class = StockMovementSerializer


class RecipeIngredientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwnerOrManager]
    queryset = RecipeIngredient.objects.all().select_related("inventory_item")
    serializer_class = RecipeIngredientSerializer
