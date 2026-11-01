import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.db import connection, connections, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Booking, GymClass, Location, Membership, Order, Plan
from .payments import fulfill_payment

def fixtures():
    user = get_user_model().objects.create_user('test@example.com', 'test@example.com', 'Strong-Pass-2026!', first_name='Test')
    other = get_user_model().objects.create_user('other@example.com', 'other@example.com', 'Strong-Pass-2026!')
    location = Location.objects.create(name='Klub', address='Warszawa', hours='6–23', maps_url='https://example.com')
    plan = Plan.objects.create(name='30 dni', description='Test', price=149, days=30)
    gym_class = GymClass.objects.create(name='HIIT', category='Cardio', trainer='Anna', location=location, starts_at=timezone.now() + timedelta(days=1), capacity=1)
    return user, other, plan, gym_class

def membership(user, plan):
    order = Order.objects.create(user=user, plan=plan, plan_name=plan.name, days=plan.days, amount=plan.price, status='paid')
    return Membership.objects.create(user=user, order=order, starts_at=timezone.now(), ends_at=timezone.now() + timedelta(days=30))

class AuthTests(TestCase):
    def setUp(self): self.client = APIClient(enforce_csrf_checks=True)
    def token(self):
        self.client.get('/api/csrf/')
        return self.client.cookies['csrftoken'].value
    def test_register_login_logout_and_csrf(self):
        payload = {'email': 'Nowy@example.com', 'name': 'Jan', 'password': 'Strong-Pass-2026!'}
        self.assertEqual(self.client.post('/api/auth/register/', payload, format='json').status_code, 403)
        result = self.client.post('/api/auth/register/', payload, format='json', HTTP_X_CSRFTOKEN=self.token())
        self.assertEqual(result.status_code, 201)
        self.assertEqual(self.client.get('/api/me/').json()['user']['email'], 'nowy@example.com')
        self.assertTrue(get_user_model().objects.get().check_password(payload['password']))
        self.assertEqual(self.client.post('/api/auth/logout/', {}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/auth/logout/', {}, format='json', HTTP_X_CSRFTOKEN=self.token()).status_code, 200)
        self.assertIsNone(self.client.get('/api/me/').json()['user'])
        self.assertEqual(self.client.post('/api/auth/login/', payload, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/auth/login/', payload, format='json', HTTP_X_CSRFTOKEN=self.token()).status_code, 200)
    def test_reject_weak_password_and_duplicate_email(self):
        token = self.token()
        data = {'email': 'jan@example.com', 'name': 'Jan', 'password': '1234567890'}
        self.assertEqual(self.client.post('/api/auth/register/', data, format='json', HTTP_X_CSRFTOKEN=token).status_code, 400)
        data['password'] = 'Strong-Pass-2026!'
        self.assertEqual(self.client.post('/api/auth/register/', data, format='json', HTTP_X_CSRFTOKEN=token).status_code, 201)
        data['email'] = 'JAN@example.com'
        self.assertEqual(self.client.post('/api/auth/register/', data, format='json', HTTP_X_CSRFTOKEN=self.token()).status_code, 400)

class BookingTests(TestCase):
    def setUp(self):
        self.user, self.other, self.plan, self.gym_class = fixtures()
        self.client = APIClient()
        self.url = f'/api/classes/{self.gym_class.pk}/book/'
    def test_auth_and_membership_required(self):
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertEqual(self.client.post('/api/checkout/', {'plan_id': 'invalid'}, format='json').status_code, 503)
    def test_capacity_duplicate_cancel_ownership_and_account_privacy(self):
        membership(self.user, self.plan); membership(self.other, self.plan)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(self.url).status_code, 201)
        self.assertEqual(self.client.post(self.url).status_code, 400)
        booking = Booking.objects.get()
        self.assertEqual(self.client.get('/api/catalog/').json()['classes'][0]['available'], 0)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 409)
        self.assertEqual(self.client.delete(f'/api/bookings/{booking.pk}/').status_code, 404)
        self.assertEqual(self.client.get('/api/me/').json()['bookings'], [])
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.delete(f'/api/bookings/{booking.pk}/').status_code, 204)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 201)
    def test_membership_must_cover_class_time(self):
        member = membership(self.user, self.plan)
        member.ends_at = timezone.now() + timedelta(hours=1); member.save()
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(self.url).status_code, 403)
    def test_past_class_cannot_be_booked_or_cancelled(self):
        membership(self.user, self.plan)
        self.client.force_authenticate(self.user)
        self.client.post(self.url)
        self.gym_class.starts_at = timezone.now() - timedelta(hours=1); self.gym_class.save()
        self.assertEqual(self.client.post(self.url).status_code, 400)
        self.assertEqual(self.client.delete(f'/api/bookings/{Booking.objects.get().pk}/').status_code, 400)

@override_settings(STRIPE_SECRET_KEY='sk_test_example', STRIPE_WEBHOOK_SECRET='whsec_test')
class PaymentTests(TestCase):
    def setUp(self):
        self.user, self.other, self.plan, self.gym_class = fixtures()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.order = Order.objects.create(user=self.user, plan=self.plan, plan_name=self.plan.name, days=self.plan.days, amount=149, stripe_session_id='cs_test_123')
        self.session = {'id': 'cs_test_123', 'payment_status': 'paid', 'amount_total': 14900, 'currency': 'pln', 'metadata': {'order_id': str(self.order.pk)}}
    def post_event(self, session=None, livemode=False):
        event = {'type': 'checkout.session.completed', 'livemode': livemode, 'data': {'object': session or self.session}}
        payload = json.dumps(event).encode()
        timestamp = str(int(time.time()))
        signature = hmac.new(b'whsec_test', timestamp.encode() + b'.' + payload, hashlib.sha256).hexdigest()
        return self.client.post('/api/stripe/webhook/', payload, content_type='application/json', HTTP_STRIPE_SIGNATURE=f't={timestamp},v1={signature}')
    def test_signed_webhook_activates_once(self):
        self.assertEqual(self.post_event().status_code, 200)
        first_end = Membership.objects.get().ends_at
        self.assertEqual(self.post_event().status_code, 200)
        self.assertEqual(Membership.objects.count(), 1)
        self.assertEqual(Membership.objects.get().ends_at, first_end)
        self.order.refresh_from_db(); self.assertEqual(self.order.status, 'paid')
    def test_reject_signature_and_live_events(self):
        self.assertEqual(self.client.post('/api/stripe/webhook/', {}, format='json').status_code, 400)
        self.assertEqual(self.post_event(livemode=True).status_code, 400)
        self.assertFalse(Membership.objects.exists())
    def test_reject_amount_currency_session_mismatch_and_ignore_unpaid(self):
        for change in [{'amount_total': 1}, {'currency': 'eur'}, {'id': 'cs_other'}]:
            self.assertEqual(self.post_event({**self.session, **change}).status_code, 400)
        self.assertEqual(self.post_event({**self.session, 'payment_status': 'unpaid'}).status_code, 200)
        self.assertFalse(Membership.objects.exists())
    def test_membership_extension_uses_purchase_snapshot(self):
        existing = membership(self.user, self.plan)
        self.plan.days = 1; self.plan.price = Decimal('1'); self.plan.save()
        fulfill_payment(self.session)
        new = Membership.objects.get(order=self.order)
        self.assertEqual(new.starts_at, existing.ends_at)
        self.assertEqual(new.ends_at - new.starts_at, timedelta(days=30))
    @patch('gym.views.stripe.checkout.Session.create')
    def test_checkout_uses_server_price(self, create):
        create.return_value.id = 'cs_test_new'
        create.return_value.url = 'https://checkout.stripe.com/test'
        response = self.client.post('/api/checkout/', {'plan_id': self.plan.pk, 'amount': 1}, format='json')
        self.assertEqual(response.status_code, 200)
        kwargs = create.call_args.kwargs
        self.assertEqual(kwargs['line_items'][0]['price_data']['unit_amount'], 14900)
        self.assertFalse(Membership.objects.exists())
    def test_invalid_plan_input(self):
        self.assertEqual(self.client.post('/api/checkout/', {'plan_id': {}}, format='json').status_code, 400)
    def test_invalid_order_id(self):
        self.assertEqual(self.post_event({**self.session, 'metadata': {'order_id': 'bad'}}).status_code, 400)

class PostgresConcurrencyTests(TransactionTestCase):
    def test_only_one_person_can_book_last_place(self):
        if connection.vendor != 'postgresql': self.skipTest('Wymaga PostgreSQL; uruchamiany w CI.')
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        user, other, plan, gym_class = fixtures()
        membership(user, plan); membership(other, plan)
        barrier = Barrier(2)
        def book(user_id):
            close_old_connections()
            try:
                client = APIClient(); client.force_authenticate(get_user_model().objects.get(pk=user_id))
                barrier.wait(timeout=10)
                return client.post(f'/api/classes/{gym_class.pk}/book/').status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(book, [user.pk, other.pk]))
        self.assertEqual(sorted(outcomes), [201, 409])
        self.assertEqual(Booking.objects.count(), 1)

class AdminBootstrapTests(TestCase):
    @patch.dict(os.environ, {'ADMIN_EMAIL': '', 'ADMIN_PASSWORD': ''})
    def test_no_public_default_account(self):
        call_command('bootstrap_admin')
        self.assertFalse(get_user_model().objects.exists())

    @patch.dict(os.environ, {'ADMIN_EMAIL': 'owner@example.com', 'ADMIN_PASSWORD': 'Strong-Owner-Pass-2026!'})
    def test_creates_admin_once_without_resetting_password(self):
        call_command('bootstrap_admin')
        user = get_user_model().objects.get()
        original_hash = user.password
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password('Strong-Owner-Pass-2026!'))
        call_command('bootstrap_admin')
        user.refresh_from_db()
        self.assertEqual(user.password, original_hash)
        self.assertEqual(get_user_model().objects.count(), 1)

    @patch.dict(os.environ, {'ADMIN_EMAIL': 'owner@example.com', 'ADMIN_PASSWORD': 'Strong-Owner-Pass-2026!'})
    def test_does_not_promote_existing_customer(self):
        user = get_user_model().objects.create_user('owner@example.com', 'owner@example.com', 'Customer-Pass-2026!')
        with self.assertRaises(CommandError): call_command('bootstrap_admin')
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
