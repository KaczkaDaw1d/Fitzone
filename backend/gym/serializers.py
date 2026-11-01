from rest_framework import serializers
from .models import Location, Plan, GymClass, Booking, Order, Membership

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'hours', 'maps_url']

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ['id', 'name', 'description', 'price', 'days', 'featured']

class ClassSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    available = serializers.SerializerMethodField()
    booked = serializers.SerializerMethodField()
    def get_available(self, obj): return max(0, obj.capacity - obj.booked_count)
    def get_booked(self, obj):
        return obj.id in self.context.get('booked_ids', set())
    class Meta:
        model = GymClass
        fields = ['id', 'name', 'category', 'trainer', 'location', 'starts_at', 'duration', 'capacity', 'available', 'booked']

class BookingSerializer(serializers.ModelSerializer):
    gym_class = ClassSerializer(read_only=True)
    class Meta:
        model = Booking
        fields = ['id', 'gym_class']

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'plan_name', 'amount', 'currency', 'status', 'created_at']

class MembershipSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='order.plan_name')
    class Meta:
        model = Membership
        fields = ['id', 'plan_name', 'starts_at', 'ends_at']
