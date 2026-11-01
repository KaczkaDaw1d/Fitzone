from django.urls import path
from . import views
urlpatterns = [
    path('health/', views.health), path('csrf/', views.csrf),
    path('auth/register/', views.RegisterView.as_view()), path('auth/login/', views.LoginView.as_view()),
    path('auth/logout/', views.LogoutView.as_view()), path('me/', views.MeView.as_view()),
    path('catalog/', views.CatalogView.as_view()),
    path('classes/<int:class_id>/book/', views.BookingView.as_view()),
    path('bookings/<int:booking_id>/', views.CancelBookingView.as_view()),
    path('checkout/', views.CheckoutView.as_view()), path('stripe/webhook/', views.stripe_webhook),
]
