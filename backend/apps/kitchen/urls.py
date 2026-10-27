from django.urls import path

from . import views

urlpatterns = [
    path("tickets/", views.KitchenTicketList.as_view(), name="kitchen-ticket-list"),
    path(
        "tickets/<int:line_id>/preparing/",
        views.MarkPreparing.as_view(),
        name="kitchen-mark-preparing",
    ),
    path("tickets/<int:line_id>/ready/", views.MarkReady.as_view(), name="kitchen-mark-ready"),
    path("tickets/<int:line_id>/served/", views.MarkServed.as_view(), name="kitchen-mark-served"),
]
