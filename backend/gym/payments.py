from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import Membership, Order

@transaction.atomic
def fulfill_payment(session):
    """Called only with a signature-verified Stripe event; safe on repeated delivery."""
    order_id = session.get('metadata', {}).get('order_id')
    if not order_id or session.get('payment_status') != 'paid':
        return
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.status == Order.Status.PAID:
        return
    if (order.stripe_session_id != session.get('id')
        or int(order.amount * 100) != session.get('amount_total')
        or order.currency != session.get('currency')):
        raise ValueError('Płatność nie odpowiada zamówieniu.')
    # Serialize concurrent purchases by the same user and append membership time.
    get_user_model().objects.select_for_update().get(pk=order.user_id)
    now = timezone.now()
    last = Membership.objects.filter(user=order.user, ends_at__gt=now).order_by('-ends_at').first()
    start = last.ends_at if last else now
    Membership.objects.create(user=order.user, order=order, starts_at=start, ends_at=start + timedelta(days=order.days))
    order.status = Order.Status.PAID
    order.save(update_fields=['status'])
