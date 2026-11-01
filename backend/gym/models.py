import uuid
from django.conf import settings
from django.db import models

class Location(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    hours = models.CharField(max_length=100)
    maps_url = models.URLField()
    def __str__(self): return self.name

class Plan(models.Model):
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=250)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    days = models.PositiveIntegerField()
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0, days__gt=0), name='positive_plan_price_days')]
    def __str__(self): return self.name

class GymClass(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    trainer = models.CharField(max_length=100)
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    duration = models.PositiveIntegerField(default=60)
    capacity = models.PositiveIntegerField(default=16)
    class Meta:
        ordering = ['starts_at']
        constraints = [models.CheckConstraint(condition=models.Q(capacity__gt=0, duration__gt=0), name='positive_class_capacity_duration')]
    def __str__(self): return f'{self.name} · {self.starts_at:%d.%m %H:%M}'

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Oczekuje'
        PAID = 'paid', 'Opłacone'
        FAILED = 'failed', 'Nieudane'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    plan_name = models.CharField(max_length=80)
    days = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3, default='pln')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order = models.OneToOneField(Order, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(ends_at__gt=models.F('starts_at')), name='membership_positive_interval')]

class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    gym_class = models.ForeignKey(GymClass, on_delete=models.CASCADE, related_name='bookings')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'gym_class'], name='unique_user_class')]
