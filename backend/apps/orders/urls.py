from django.urls import path

from . import views

urlpatterns = [
    path("", views.OrderList.as_view(), name="order-list"),
    path("tables/<int:table_id>/active/", views.ActiveTableOrder.as_view(), name="order-active"),
    path("tables/<int:table_id>/open/", views.OpenTableOrder.as_view(), name="order-open"),
    path("batches/", views.BatchList.as_view(), name="order-batch-list"),
    path("batches/<uuid:pk>/", views.BatchDetail.as_view(), name="order-batch-detail"),
    path("batches/<uuid:pk>/approve/", views.ReviewBatch.as_view(), name="order-batch-approve"),
    path("batches/<uuid:pk>/reject/", views.RejectBatch.as_view(), name="order-batch-reject"),
    path("<uuid:pk>/", views.OrderDetail.as_view(), name="order-detail"),
    path("<uuid:pk>/batches/", views.SubmitBatch.as_view(), name="order-submit"),
]
