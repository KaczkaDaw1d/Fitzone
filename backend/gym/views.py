import logging
import stripe
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from .models import Booking, GymClass, Location, Membership, Order, Plan
from .serializers import ClassSerializer, LocationSerializer, MembershipSerializer, OrderSerializer, PlanSerializer
from .payments import fulfill_payment

logger = logging.getLogger(__name__)
User = get_user_model()

@ensure_csrf_cookie
def csrf(request): return JsonResponse({'detail': 'OK'})

def user_data(user):
    return {'id': user.pk, 'email': user.email, 'name': user.first_name,
            'is_staff': user.is_staff, 'date_joined': user.date_joined.isoformat()}

class Credentials(serializers.Serializer):
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    name = serializers.CharField(max_length=100, required=False)

@method_decorator(csrf_protect, name='dispatch')
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'
    def post(self, request):
        data = Credentials(data=request.data)
        data.is_valid(raise_exception=True)
        email = data.validated_data['email'].lower()
        name = data.validated_data.get('name', '').strip()
        if not name: return Response({'detail': 'Podaj imię.'}, status=400)
        user = User(username=email, email=email, first_name=name)
        try:
            validate_password(data.validated_data['password'], user)
        except ValidationError as exc:
            return Response({'detail': ' '.join(exc.messages)}, status=400)
        try:
            with transaction.atomic():
                user.set_password(data.validated_data['password'])
                user.save()
        except IntegrityError:
            return Response({'detail': 'Nie można utworzyć konta z tym adresem e-mail.'}, status=400)
        login(request, user)
        return Response(user_data(user), status=201)

@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'
    def post(self, request):
        data = Credentials(data=request.data)
        data.is_valid(raise_exception=True)
        user = authenticate(request, username=data.validated_data['email'].lower(), password=data.validated_data['password'])
        if not user: return Response({'detail': 'Nieprawidłowy e-mail lub hasło.'}, status=400)
        login(request, user)
        return Response(user_data(user))

class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detail': 'Wylogowano.'})

class PasswordChangeInput(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    new_password_confirm = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)

class ChangePasswordView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    @transaction.atomic
    def post(self, request):
        data = PasswordChangeInput(data=request.data)
        data.is_valid(raise_exception=True)
        # Read the current hash under a lock, including for simultaneous changes.
        user = User.objects.select_for_update().get(pk=request.user.pk)
        if not user.check_password(data.validated_data['old_password']):
            return Response({'detail': 'Obecne hasło jest nieprawidłowe.'}, status=400)
        password = data.validated_data['new_password']
        if password != data.validated_data['new_password_confirm']:
            return Response({'detail': 'Nowe hasła muszą być takie same.'}, status=400)
        if user.check_password(password):
            return Response({'detail': 'Nowe hasło musi różnić się od obecnego.'}, status=400)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            return Response({'detail': ' '.join(exc.messages)}, status=400)
        user.set_password(password)
        user.save(update_fields=['password'])
        # Preserve this session; other sessions fail their auth hash check.
        update_session_auth_hash(request, user)
        return Response({'detail': 'Hasło zostało zmienione. Pozostajesz zalogowany.'})

class MeView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        if not request.user.is_authenticated: return Response({'user': None})
        memberships = Membership.objects.filter(user=request.user, ends_at__gt=timezone.now()).select_related('order').order_by('starts_at')
        bookings = Booking.objects.filter(user=request.user, gym_class__starts_at__gt=timezone.now()).select_related('gym_class__location').order_by('gym_class__starts_at')
        classes = GymClass.objects.filter(pk__in=bookings.values('gym_class_id')).select_related('location').annotate(booked_count=Count('bookings'))
        class_map = {c.pk: c for c in classes}
        context = {'booked_ids': set(class_map)}
        return Response({
            'user': user_data(request.user),
            'memberships': MembershipSerializer(memberships, many=True).data,
            'bookings': [{'id': b.pk, 'gym_class': ClassSerializer(class_map[b.gym_class_id], context=context).data} for b in bookings],
            'orders': OrderSerializer(Order.objects.filter(user=request.user)[:30], many=True).data,
        })

class CatalogView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        classes = GymClass.objects.filter(starts_at__gt=timezone.now()).select_related('location').annotate(booked_count=Count('bookings'))[:200]
        booked = set(Booking.objects.filter(user=request.user).values_list('gym_class_id', flat=True)) if request.user.is_authenticated else set()
        return Response({
            'locations': LocationSerializer(Location.objects.all(), many=True).data,
            'plans': PlanSerializer(Plan.objects.filter(active=True).order_by('price'), many=True).data,
            'classes': ClassSerializer(classes, many=True, context={'booked_ids': booked}).data,
            'payments_enabled': bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET),
        })

class BookingView(APIView):
    @transaction.atomic
    def post(self, request, class_id):
        gym_class = get_object_or_404(GymClass.objects.select_for_update(), pk=class_id)
        if gym_class.starts_at <= timezone.now(): return Response({'detail': 'Zajęcia już się rozpoczęły.'}, status=400)
        if not Membership.objects.filter(user=request.user, starts_at__lte=gym_class.starts_at, ends_at__gt=gym_class.starts_at).exists():
            return Response({'detail': 'Potrzebujesz karnetu ważnego w dniu zajęć.'}, status=403)
        if Booking.objects.filter(user=request.user, gym_class=gym_class).exists():
            return Response({'detail': 'Masz już rezerwację na te zajęcia.'}, status=400)
        if gym_class.bookings.count() >= gym_class.capacity:
            return Response({'detail': 'Brak wolnych miejsc.'}, status=409)
        booking = Booking.objects.create(user=request.user, gym_class=gym_class)
        return Response({'id': booking.pk}, status=201)

class CancelBookingView(APIView):
    @transaction.atomic
    def delete(self, request, booking_id):
        booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
        gym_class = GymClass.objects.select_for_update().get(pk=booking.gym_class_id)
        if gym_class.starts_at <= timezone.now(): return Response({'detail': 'Nie można anulować rozpoczętych zajęć.'}, status=400)
        booking.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CheckoutInput(serializers.Serializer):
    plan_id = serializers.IntegerField(min_value=1)

class CheckoutView(APIView):
    def post(self, request):
        if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
            return Response({'detail': 'Płatności testowe wymagają konfiguracji Stripe przez administratora.'}, status=503)
        data = CheckoutInput(data=request.data)
        data.is_valid(raise_exception=True)
        plan = get_object_or_404(Plan, pk=data.validated_data['plan_id'], active=True)
        order = Order.objects.create(user=request.user, plan=plan, plan_name=plan.name, days=plan.days, amount=plan.price)
        try:
            client = stripe.StripeClient(settings.STRIPE_SECRET_KEY)
            session = client.v1.checkout.sessions.create(
                params={
                    'mode': 'payment',
                    'customer_email': request.user.email,
                    'line_items': [{'price_data': {'currency': 'pln', 'unit_amount': int(order.amount * 100),
                        'product_data': {'name': f'FitZone · {order.plan_name}'}}, 'quantity': 1}],
                    'metadata': {'order_id': str(order.pk)},
                    'success_url': settings.PUBLIC_URL + f'/?payment=success&order={order.pk}#konto',
                    'cancel_url': settings.PUBLIC_URL + '/?payment=cancelled#karnety',
                    'integration_identifier': settings.STRIPE_INTEGRATION_IDENTIFIER,
                },
                options={'idempotency_key': str(order.pk)},
            )
        except stripe.StripeError:
            order.status = Order.Status.FAILED
            order.save(update_fields=['status'])
            logger.warning('Stripe checkout failed for order %s', order.pk)
            return Response({'detail': 'Nie udało się rozpocząć płatności. Spróbuj ponownie.'}, status=502)
        order.stripe_session_id = session.id
        order.save(update_fields=['stripe_session_id'])
        return Response({'url': session.url})

@csrf_exempt
@require_POST
def stripe_webhook(request):
    if not settings.STRIPE_WEBHOOK_SECRET: return JsonResponse({'detail': 'Stripe nie skonfigurowany.'}, status=503)
    try:
        event = stripe.Webhook.construct_event(request.body, request.headers.get('Stripe-Signature', ''), settings.STRIPE_WEBHOOK_SECRET).to_dict()
    except (ValueError, stripe.SignatureVerificationError):
        return JsonResponse({'detail': 'Niepoprawny podpis.'}, status=400)
    if event.get('livemode'):
        return JsonResponse({'detail': 'Wyłącznie płatności testowe.'}, status=400)
    if event['type'] in ('checkout.session.completed', 'checkout.session.async_payment_succeeded',
                         'checkout.session.async_payment_failed', 'checkout.session.expired'):
        try:
            session = event['data']['object']
            if event['type'] in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
                fulfill_payment(session)
            else:
                order_id = session.get('metadata', {}).get('order_id')
                if order_id:
                    Order.objects.filter(pk=order_id, stripe_session_id=session.get('id'),
                        status=Order.Status.PENDING).update(status=Order.Status.FAILED)
        except (Order.DoesNotExist, ValueError, ValidationError):
            logger.warning('Rejected payment webhook')
            return JsonResponse({'detail': 'Nie można potwierdzić zamówienia.'}, status=400)
    return JsonResponse({'received': True})

def health(request): return JsonResponse({'status': 'ok'})

