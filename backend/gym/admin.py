from django.contrib import admin
from .models import Location, Plan, GymClass, Booking, Order, Membership

admin.site.site_header = 'FitZone · administracja'
admin.site.site_title = 'FitZone'

@admin.register(GymClass)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'trainer', 'location', 'starts_at', 'capacity']
    list_filter = ['location', 'category']
    search_fields = ['name', 'trainer']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'plan_name', 'amount', 'status', 'created_at']
    list_filter = ['status']
    readonly_fields = [field.name for field in Order._meta.fields]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'order', 'starts_at', 'ends_at']
    readonly_fields = [field.name for field in Membership._meta.fields]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False

admin.site.register([Location, Plan, Booking])
