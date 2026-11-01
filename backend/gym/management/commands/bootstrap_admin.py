import os
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

class Command(BaseCommand):
    help = 'Opcjonalnie tworzy administratora z ADMIN_EMAIL i ADMIN_PASSWORD. Nie zmienia istniejących kont.'
    def handle(self, *args, **kwargs):
        email = os.getenv('ADMIN_EMAIL', '').strip().lower()
        password = os.getenv('ADMIN_PASSWORD', '')
        if not email and not password:
            return
        if not email or not password:
            raise CommandError('Ustaw obie zmienne ADMIN_EMAIL i ADMIN_PASSWORD albo usuń obie.')
        User = get_user_model()
        existing = User.objects.filter(username=email).first()
        if existing:
            if not existing.is_superuser:
                raise CommandError('Istniejącego konta klienta nie można automatycznie zmienić w administratora.')
            return
        user = User(username=email, email=email, is_staff=True, is_superuser=True)
        try:
            validate_email(email)
            validate_password(password, user)
        except ValidationError:
            raise CommandError('Niepoprawny e-mail lub zbyt słabe hasło administratora.') from None
        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS('Utworzono konto administratora.'))
