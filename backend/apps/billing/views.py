from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole, IsCashier
from apps.billing.models import Bill
from apps.billing.serializers import (
    BillSerializer,
    PaymentCreateSerializer,
    PaymentSerializer,
    PrintEventSerializer,
)
from apps.billing.services import (
    checkout_table,
    finalize_bill,
    generate_draft_bill,
    record_payment,
    record_print,
)
from apps.orders.models import DiningSession


class CanReadBilling(HasRole):
    allowed_roles = ("cashier", "manager", "owner")


def _get_bill_for_session(session_id):
    # Generates/updates the draft or returns the finalized/paid bill
    try:
        bill = generate_draft_bill(session_id=session_id)
        return bill
    except Exception:
        # If it's closed or can't be generated, just get the existing one
        return Bill.objects.filter(session_id=session_id).first()


class ActiveTableBills(APIView):
    permission_classes = [CanReadBilling]

    def get(self, request):
        active_sessions = DiningSession.objects.filter(state=DiningSession.State.OPEN).select_related("table")
        bills = []
        for session in active_sessions:
            bill = _get_bill_for_session(session.id)
            if bill:
                bills.append(bill)

        return Response(BillSerializer(bills, many=True).data)


class BillDetailBySession(APIView):
    permission_classes = [CanReadBilling]

    def get(self, request, session_id):
        bill = _get_bill_for_session(session_id)
        if not bill:
            return Response({"detail": "No bill found for this session."}, status=404)
        return Response(BillSerializer(bill).data)


class BillFinalize(APIView):
    permission_classes = [IsCashier]

    def post(self, request, bill_id):
        bill = finalize_bill(bill_id=bill_id, actor=request.user)
        return Response(BillSerializer(bill).data)


class BillPayment(APIView):
    permission_classes = [IsCashier]

    def post(self, request, bill_id):
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = record_payment(
            bill_id=bill_id,
            actor=request.user,
            amount=serializer.validated_data["amount"],
            method=serializer.validated_data["method"],
            idempotency_key=serializer.validated_data["idempotency_key"],
            manual_reference=serializer.validated_data.get("manual_reference", "")
        )
        return Response(PaymentSerializer(payment).data, status=201)


class BillCheckout(APIView):
    permission_classes = [IsCashier]

    def post(self, request, session_id):
        session, success = checkout_table(session_id=session_id, actor=request.user)
        return Response({"success": success})


class BillPrint(APIView):
    permission_classes = [IsCashier]

    def post(self, request, bill_id):
        event = record_print(bill_id=bill_id, actor=request.user)
        return Response(PrintEventSerializer(event).data, status=201)
