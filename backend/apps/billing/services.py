import uuid
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.accounts.permissions import IsCashier
from apps.billing.models import Bill, BillLine, Payment, PrintEvent
from apps.orders.models import DiningSession, OrderBatch, OrderLine
from apps.restaurants.models import DiningTable


class BillingConflict(APIException):
    status_code = 409
    default_detail = "Billing conflict occurred. Please retry."
    default_code = "billing_conflict"


def require_role(actor, permission):
    from types import SimpleNamespace
    if not permission().has_permission(SimpleNamespace(user=actor), None):
        raise PermissionDenied("Your role cannot perform this billing action.")


def _generate_human_id(session_id):
    # Short human-readable ID for the bill based on session UUID (e.g. last 8 chars)
    return f"B-{str(session_id).split('-')[-1].upper()}"


@transaction.atomic
def generate_draft_bill(*, session_id):
    """
    Generate or update a draft bill for an open dining session.
    Only approved & served items are eligible.
    """
    session = get_object_or_404(DiningSession.objects.select_for_update(), pk=session_id)
    if session.state != DiningSession.State.OPEN:
        raise ValidationError({"detail": "Cannot generate bill for closed dining session."})

    bill, created = Bill.objects.select_for_update().get_or_create(
        session=session,
        defaults={"human_id": _generate_human_id(session.id), "status": Bill.Status.DRAFT}
    )

    if bill.status != Bill.Status.DRAFT:
        raise BillingConflict("Bill is already finalized or paid.")

    # Find eligible lines: approved and served
    eligible_lines = OrderLine.objects.filter(
        batch__order__session=session,
        batch__status=OrderBatch.Status.APPROVED,
        kitchen_ticket__status="served"
    ).select_related("kitchen_ticket")

    # Update BillLines to match eligible lines
    existing_bill_lines = {bl.order_line_id: bl for bl in bill.lines.all()}

    current_line_ids = set()
    for oline in eligible_lines:
        current_line_ids.add(oline.id)
        if oline.id not in existing_bill_lines:
            BillLine.objects.create(
                bill=bill,
                order_line=oline,
                item_name=oline.item_name,
                quantity=oline.quantity,
                unit_price=oline.unit_price,
                line_total=oline.line_total
            )

    # Remove any BillLines that are no longer eligible (e.g., if somehow un-served, though impossible in current lifecycle, good for consistency)
    lines_to_remove = set(existing_bill_lines.keys()) - current_line_ids
    if lines_to_remove:
        BillLine.objects.filter(bill=bill, order_line_id__in=lines_to_remove).delete()

    # Recalculate totals
    bill.refresh_from_db()
    subtotal = sum(bl.line_total for bl in bill.lines.all())

    # Financial calculation rules (Configuration: 13% VAT, 10% Service Charge, etc - making it simple configurable logic)
    # Using basic logic: subtotal + 10% SC = taxable. taxable + 13% VAT = grand_total.
    # We'll use 0 for now unless explicit configuration is provided. Assuming 0% tax/sc for now.
    discount = Decimal("0.00")
    taxable = subtotal - discount
    tax = Decimal("0.00")
    service_charge = Decimal("0.00")
    grand_total = taxable + tax + service_charge

    bill.subtotal = subtotal
    bill.discount_amount = discount
    bill.taxable_amount = taxable
    bill.tax_amount = tax
    bill.service_charge = service_charge
    bill.grand_total = grand_total
    bill.save()

    return bill


@transaction.atomic
def finalize_bill(*, bill_id, actor):
    require_role(actor, IsCashier)
    bill = get_object_or_404(Bill.objects.select_for_update(), pk=bill_id)

    if bill.session.state != DiningSession.State.OPEN:
        raise BillingConflict("Dining session is closed.")

    if bill.status != Bill.Status.DRAFT:
        return bill # Idempotent or already finalized

    # Regenerate one last time to ensure we have the latest items
    bill = generate_draft_bill(session_id=bill.session_id)

    # Check for any unresolved items
    unresolved = OrderLine.objects.filter(
        batch__order__session_id=bill.session_id,
        batch__status=OrderBatch.Status.APPROVED
    ).exclude(kitchen_ticket__status="served").exists()

    if unresolved:
        raise ValidationError({"detail": "Cannot finalize bill. There are unresolved kitchen items."})

    bill.status = Bill.Status.FINALIZED
    bill.finalized_by = actor
    bill.finalized_at = timezone.now()
    bill.save(update_fields=["status", "finalized_by", "finalized_at"])

    return bill


@transaction.atomic
def record_payment(*, bill_id, actor, amount, method, idempotency_key, manual_reference=""):
    require_role(actor, IsCashier)

    try:
        key = uuid.UUID(str(idempotency_key))
    except (ValueError, TypeError, AttributeError) as error:
        raise ValidationError({"detail": "A valid UUID idempotency key is required."}) from error

    bill = get_object_or_404(Bill.objects.select_for_update(), pk=bill_id)

    existing_payment = Payment.objects.filter(idempotency_key=key).first()
    if existing_payment:
        if existing_payment.bill_id != bill.id:
            raise BillingConflict("Idempotency key reused for different bill.")
        return existing_payment

    if bill.status == Bill.Status.DRAFT:
        raise ValidationError({"detail": "Cannot pay a draft bill. Finalize it first."})

    if bill.status == Bill.Status.PAID:
        raise BillingConflict("Bill is already fully paid.")

    amount = Decimal(amount)
    if amount <= 0:
        raise ValidationError({"detail": "Payment amount must be positive."})

    if amount > bill.outstanding_amount:
        raise ValidationError({"detail": "Payment amount exceeds outstanding balance."})

    payment = Payment.objects.create(
        bill=bill,
        amount=amount,
        method=method,
        received_by=actor,
        manual_reference=manual_reference,
        idempotency_key=key
    )

    bill.paid_amount += amount
    if bill.paid_amount >= bill.grand_total:
        bill.status = Bill.Status.PAID
    else:
        bill.status = Bill.Status.PARTIALLY_PAID

    bill.save(update_fields=["paid_amount", "status"])

    return payment


@transaction.atomic
def checkout_table(*, session_id, actor):
    require_role(actor, IsCashier)
    session = get_object_or_404(DiningSession.objects.select_for_update(), pk=session_id)
    table = get_object_or_404(DiningTable.objects.select_for_update(), pk=session.table_id)

    if session.state == DiningSession.State.CLOSED:
        return session, False

    bill = Bill.objects.filter(session=session).first()
    if not bill or bill.status != Bill.Status.PAID:
        raise ValidationError({"detail": "Bill must be fully paid before checkout."})

    # Ensure no unresolved items
    unresolved = OrderLine.objects.filter(
        batch__order__session=session,
        batch__status=OrderBatch.Status.APPROVED
    ).exclude(kitchen_ticket__status="served").exists()

    if unresolved:
        raise ValidationError({"detail": "Cannot checkout. Unresolved kitchen items exist."})

    # Close session
    session.state = DiningSession.State.CLOSED
    session.closed_by = actor
    session.closed_at = timezone.now()
    session.save(update_fields=["state", "closed_by", "closed_at"])

    # Free table
    table.status = DiningTable.Status.AVAILABLE
    table.save(update_fields=["status", "updated_at"])

    return session, True


def record_print(*, bill_id, actor):
    require_role(actor, IsCashier)
    bill = get_object_or_404(Bill, pk=bill_id)
    if bill.status == Bill.Status.DRAFT:
        raise ValidationError({"detail": "Cannot print a draft bill."})

    event = PrintEvent.objects.create(bill=bill, requested_by=actor)
    return event
