import random
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from marketplace.models import (
    OwnerProfile,
    CaregiverProfile,
    ServiceType,
    CaregiverService,
    CaregiverAvailability,
    Pet,
)


class Command(BaseCommand):
    help = 'Generate demo users, caregivers, pets, and services for exploration.'

    def handle(self, *args, **options):
        service_types = [
            ('dog_walk', 'Dog Walk'),
            ('drop_in', 'Drop In'),
            ('boarding', 'Boarding'),
        ]
        for code, name in service_types:
            ServiceType.objects.get_or_create(
                code=code,
                defaults={'name': name, 'description': name, 'base_duration_minutes': 60, 'default_base_price': Decimal('20.00')},
            )

        for idx in range(1, 4):
            owner_user, _ = User.objects.get_or_create(username=f'owner{idx}')
            owner_user.set_password('password')
            owner_user.save()
            OwnerProfile.objects.get_or_create(
                user=owner_user,
                defaults={
                    'phone': '000',
                    'country': 'US',
                    'city': 'NYC',
                    'address_line1': '123 St',
                    'postal_code': '10000',
                },
            )

        for idx in range(1, 4):
            caregiver_user, _ = User.objects.get_or_create(username=f'caregiver{idx}')
            caregiver_user.set_password('password')
            caregiver_user.save()
            caregiver, _ = CaregiverProfile.objects.get_or_create(
                user=caregiver_user,
                defaults={
                    'phone': '111',
                    'city': 'NYC',
                    'bio': 'Experienced pet lover',
                    'years_experience': 2,
                    'hourly_rate_base': Decimal('18.00'),
                    'services_offered': ['dog_walk', 'drop_in'],
                    'max_pets': 2,
                    'accepts_large_dogs': True,
                    'gps_radius_km': Decimal('5.0'),
                },
            )
            for service_type in ServiceType.objects.all():
                CaregiverService.objects.get_or_create(
                    caregiver=caregiver,
                    service_type=service_type,
                    defaults={'price_per_unit': service_type.default_base_price, 'is_active': True},
                )
            CaregiverAvailability.objects.get_or_create(
                caregiver=caregiver,
                weekday=timezone.now().weekday(),
                defaults={'start_time': timezone.now().time(), 'end_time': (timezone.now() + timezone.timedelta(hours=2)).time()},
            )

        for owner in OwnerProfile.objects.all():
            Pet.objects.get_or_create(
                owner=owner,
                name=f'{owner.user.username}-pet',
                defaults={'species': 'dog', 'breed': 'Mix', 'sex': 'M', 'birthdate': timezone.now().date()},
            )
        self.stdout.write(self.style.SUCCESS('Demo data generated.'))
