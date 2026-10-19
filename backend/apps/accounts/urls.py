from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.CSRFView.as_view(), name="accounts-csrf"),
    path("login/owner/", views.OwnerLoginView.as_view(), name="accounts-owner-login"),
    path("login/staff/", views.StaffLoginView.as_view(), name="accounts-staff-login"),
    path("logout/", views.LogoutView.as_view(), name="accounts-logout"),
    path("me/", views.MeView.as_view(), name="accounts-me"),
    path("pin/change/", views.PINChangeView.as_view(), name="accounts-pin-change"),
    path(
        "password/change/", views.OwnerPasswordChangeView.as_view(), name="accounts-password-change"
    ),
    path("staff/", views.StaffListCreateView.as_view(), name="accounts-staff"),
    path("staff/<int:pk>/", views.StaffStateView.as_view(), name="accounts-staff-state"),
    path("staff/<int:pk>/pin/reset/", views.StaffPINResetView.as_view(), name="accounts-pin-reset"),
]
