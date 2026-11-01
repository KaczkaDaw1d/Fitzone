from datetime import datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from gym.models import Location, Plan, GymClass

class Command(BaseCommand):
    help = 'Dodaje przykładową ofertę i grafik na 14 dni. Nie tworzy kont ani płatności.'
    def handle(self, *args, **kwargs):
        center, _ = Location.objects.get_or_create(name='Warszawa · Centrum', defaults={
            'address': 'ul. Marszałkowska 104, Warszawa', 'hours': 'Codziennie · 06:00–23:00',
            'maps_url': 'https://www.google.com/maps/search/?api=1&query=Marszalkowska+104+Warszawa'})
        mokotow, _ = Location.objects.get_or_create(name='Warszawa · Mokotów', defaults={
            'address': 'ul. Puławska 39, Warszawa', 'hours': 'Codziennie · 06:00–23:00',
            'maps_url': 'https://www.google.com/maps/search/?api=1&query=Pulawska+39+Warszawa'})
        for name, price, days, description, featured in [
            ('Na próbę', '39.00', 1, 'Jeden dzień. Pełna energia. Poznaj swój nowy klub.', False),
            ('Twój rytm', '149.00', 30, '30 dni treningów i zajęć grupowych bez limitu.', True),
            ('Pełna moc', '389.00', 90, '90 dni regularności. Zbuduj nawyk, który zostaje.', False),
        ]:
            Plan.objects.get_or_create(name=name, defaults={'price': price, 'days': days, 'description': description, 'featured': featured})
        for offset in range(14):
            day = timezone.localdate() + timedelta(days=offset)
            for name, category, trainer, hour, minute, duration, location in [
                ('Morning Flow', 'Joga', 'Anna Nowak', 7, 30, 60, center),
                ('Strong Body', 'Siła', 'Michał Wójcik', 17, 0, 50, mokotow),
                ('HIIT the Beat', 'Cardio', 'Julia Kowalska', 18, 30, 45, center),
                ('Evening Reset', 'Mobilność', 'Anna Nowak', 20, 0, 60, mokotow),
            ]:
                start = timezone.make_aware(datetime.combine(day, time(hour, minute)))
                GymClass.objects.get_or_create(name=name, starts_at=start, location=location,
                    defaults={'category': category, 'trainer': trainer, 'duration': duration, 'capacity': 16})
        self.stdout.write(self.style.SUCCESS('Oferta i przykładowy grafik gotowe. Lokalizacje są fikcyjnymi klubami projektu.'))
