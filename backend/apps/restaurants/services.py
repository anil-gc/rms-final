from rest_framework import serializers

from .models import Restaurant


def configured_restaurant():
    restaurant = Restaurant.objects.filter(pk=1).first()
    if restaurant is None:
        raise serializers.ValidationError({"detail": "Set up the restaurant profile first."})
    return restaurant
