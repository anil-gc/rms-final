from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from apps.core.api import WorkspaceAPIView, WorkspaceModelViewSet, can_manage

from .images import LogoSerializer
from .models import DiningTable, Restaurant
from .serializers import DiningTableSerializer, RestaurantSerializer
from .services import configured_restaurant


class RestaurantProfileView(WorkspaceAPIView):
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get(self, request):
        return Response(RestaurantSerializer(get_object_or_404(Restaurant, pk=1)).data)

    def post(self, request):
        serializer = RestaurantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                # force_insert prevents a second setup request from replacing row 1.
                restaurant = Restaurant(**serializer.validated_data)
                restaurant.save(force_insert=True)
        except IntegrityError as error:
            raise serializers.ValidationError(
                {"detail": "The restaurant already exists. Refresh and edit its profile."}
            ) from error
        return Response(RestaurantSerializer(restaurant).data, status=201)

    def patch(self, request):
        with transaction.atomic():
            restaurant = get_object_or_404(Restaurant.objects.select_for_update(), pk=1)
            serializer = RestaurantSerializer(restaurant, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)


class RestaurantLogoView(WorkspaceAPIView):
    parser_classes = [MultiPartParser]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get(self, request):
        restaurant = get_object_or_404(Restaurant, pk=1)
        if not restaurant.logo:
            raise Http404
        try:
            return FileResponse(restaurant.logo.open("rb"), content_type="image/png")
        except FileNotFoundError as error:
            raise Http404 from error

    def post(self, request):
        serializer = LogoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            restaurant = get_object_or_404(Restaurant.objects.select_for_update(), pk=1)
            old = restaurant.logo.name
            storage = restaurant.logo.storage
            image = serializer.validated_data["logo"]
            restaurant.logo.save(image.name, image, save=False)
            try:
                restaurant.save(update_fields=["logo", "updated_at"])
            except Exception:
                storage.delete(restaurant.logo.name)
                raise
            if old:
                transaction.on_commit(lambda: storage.delete(old), robust=True)
        return Response(RestaurantSerializer(restaurant).data)

    def delete(self, request):
        with transaction.atomic():
            restaurant = get_object_or_404(Restaurant.objects.select_for_update(), pk=1)
            old, storage = restaurant.logo.name, restaurant.logo.storage
            restaurant.logo = ""
            restaurant.save(update_fields=["logo", "updated_at"])
            if old:
                transaction.on_commit(lambda: storage.delete(old), robust=True)
        return Response(status=204)


class DiningTableViewSet(WorkspaceModelViewSet):
    queryset = DiningTable.objects.all()
    serializer_class = DiningTableSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset if can_manage(self.request.user) else queryset.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(restaurant=configured_restaurant())
