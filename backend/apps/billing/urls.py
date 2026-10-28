from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("active-tables/", views.ActiveTableBills.as_view(), name="active-tables"),
    path(
        "session/<uuid:session_id>/",
        views.BillDetailBySession.as_view(),
        name="session-bill-detail",
    ),
    path("bill/<uuid:bill_id>/finalize/", views.BillFinalize.as_view(), name="bill-finalize"),
    path("bill/<uuid:bill_id>/payments/", views.BillPayment.as_view(), name="bill-payment"),
    path("bill/<uuid:bill_id>/print/", views.BillPrint.as_view(), name="bill-print"),
    path(
        "session/<uuid:session_id>/checkout/", views.BillCheckout.as_view(), name="session-checkout"
    ),
]
