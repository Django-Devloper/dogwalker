from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import (
    Booking,
    CaregiverAvailability,
    CaregiverProfile,
    CaregiverService,
    OwnerProfile,
    Pet,
    ServiceType,
    compute_commission,
    is_caregiver_available,
)


class BookingLogicTests(TestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(username='owner', password='pass')
        self.caregiver_user = User.objects.create_user(username='care', password='pass')
        self.owner = OwnerProfile.objects.create(
            user=self.owner_user,
            phone='123',
            country='US',
            city='NYC',
            address_line1='1 St',
            address_line2='',
            postal_code='00000',
        )
        self.caregiver = CaregiverProfile.objects.create(
            user=self.caregiver_user,
            phone='555',
            city='NYC',
            bio='',
            years_experience=3,
            hourly_rate_base=Decimal('20.00'),
            services_offered=['dog_walk'],
            max_pets=2,
            accepts_large_dogs=True,
            accepts_aggressive=False,
            gps_radius_km=Decimal('5.0'),
        )
        self.pet = Pet.objects.create(
            owner=self.owner,
            name='Fido',
            species='dog',
            breed='Mix',
            sex='M',
            birthdate=datetime.utcnow().date(),
            weight_kg=Decimal('15.0'),
            is_neutered=True,
        )
        self.service_type = ServiceType.objects.create(
            code='dog_walk',
            name='Dog Walk',
            description='Walk the dog',
            base_duration_minutes=60,
            default_base_price=Decimal('25.00'),
        )
        self.caregiver_service = CaregiverService.objects.create(
            caregiver=self.caregiver,
            service_type=self.service_type,
            price_per_unit=Decimal('30.00'),
            is_active=True,
        )
        CaregiverAvailability.objects.create(
            caregiver=self.caregiver,
            weekday=timezone.now().weekday(),
            start_time=time(8, 0),
            end_time=time(20, 0),
        )

    def test_caregiver_available(self):
        start = timezone.now() + timedelta(hours=1)
        end = start + timedelta(hours=1)
        self.assertTrue(is_caregiver_available(self.caregiver, start, end))

    def test_booking_creation_and_commission(self):
        start = timezone.now() + timedelta(hours=1)
        end = start + timedelta(hours=1)
        platform_fee, earnings = compute_commission(self.caregiver_service.price_per_unit)
        booking = Booking.objects.create(
            owner=self.owner,
            caregiver=self.caregiver,
            pet=self.pet,
            service_type=self.service_type,
            start_datetime=start,
            end_datetime=end,
            duration_minutes=60,
            status=Booking.STATUS_PENDING,
            owner_notes='',
            caregiver_notes='',
            price_subtotal=self.caregiver_service.price_per_unit,
            platform_fee=platform_fee,
            caregiver_earnings=earnings,
        )
        self.assertEqual(booking.price_subtotal, Decimal('30.00'))
        self.assertEqual(booking.caregiver_earnings + booking.platform_fee, booking.price_subtotal)

    def test_status_transitions(self):
        start = timezone.now() + timedelta(hours=1)
        end = start + timedelta(hours=1)
        platform_fee, earnings = compute_commission(self.caregiver_service.price_per_unit)
        booking = Booking.objects.create(
            owner=self.owner,
            caregiver=self.caregiver,
            pet=self.pet,
            service_type=self.service_type,
            start_datetime=start,
            end_datetime=end,
            duration_minutes=60,
            status=Booking.STATUS_PENDING,
            owner_notes='',
            caregiver_notes='',
            price_subtotal=self.caregiver_service.price_per_unit,
            platform_fee=platform_fee,
            caregiver_earnings=earnings,
        )
        booking.change_status(Booking.STATUS_ACCEPTED)
        self.assertEqual(booking.status, Booking.STATUS_ACCEPTED)
        with self.assertRaises(ValueError):
            booking.change_status(Booking.STATUS_PENDING)
        booking.change_status(Booking.STATUS_COMPLETED)
        self.assertEqual(booking.status, Booking.STATUS_COMPLETED)
