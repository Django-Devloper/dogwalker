"""Domain models for the pet care marketplace."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.db.models import Avg, Count
from django.db.models.functions import Coalesce
from django.contrib.postgres.fields import ArrayField


class BaseModel(models.Model):
    """Base model that uses UUID primary keys for consistency."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(BaseModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OwnerProfile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, db_index=True)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    postal_code = models.CharField(max_length=20)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"OwnerProfile({self.user.username})"


class CaregiverProfile(BaseModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30)
    city = models.CharField(max_length=100, db_index=True)
    bio = models.TextField(blank=True)
    years_experience = models.PositiveIntegerField(default=0)
    hourly_rate_base = models.DecimalField(max_digits=10, decimal_places=2)
    services_offered = models.JSONField(default=list)
    max_pets = models.PositiveIntegerField(default=1)
    accepts_large_dogs = models.BooleanField(default=False)
    accepts_aggressive = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    rating_count = models.PositiveIntegerField(default=0)
    gps_radius_km = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"CaregiverProfile({self.user.username})"

    @transaction.atomic
    def recalc_ratings(self) -> None:
        """Recalculate rating aggregates from reviews."""
        aggregates = Review.objects.filter(target_caregiver=self).aggregate(
            avg=Coalesce(Avg('rating'), 0), count=Coalesce(Count('id'), 0)
        )
        self.rating_average = Decimal(aggregates['avg']).quantize(Decimal('0.01')) if aggregates['avg'] else Decimal('0.00')
        self.rating_count = aggregates['count']
        self.save(update_fields=['rating_average', 'rating_count'])


class Pet(TimestampedModel):
    SPECIES_CHOICES = [
        ('dog', 'Dog'),
        ('cat', 'Cat'),
        ('other', 'Other'),
    ]

    SEX_CHOICES = [('M', 'Male'), ('F', 'Female')]

    owner = models.ForeignKey(OwnerProfile, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=20, choices=SPECIES_CHOICES)
    breed = models.CharField(max_length=100, blank=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    birthdate = models.DateField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_neutered = models.BooleanField(default=False)
    medical_notes = models.TextField(blank=True)
    behavior_notes = models.TextField(blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class ServiceType(BaseModel):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_duration_minutes = models.PositiveIntegerField(default=60)
    default_base_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:  # pragma: no cover
        return self.name


class CaregiverService(BaseModel):
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='services')
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='caregiver_services')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('caregiver', 'service_type')

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.caregiver} - {self.service_type}"


class ServiceArea(BaseModel):
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='service_areas')
    city = models.CharField(max_length=100, db_index=True)
    country = models.CharField(max_length=100)
    geo_center_lat = models.DecimalField(max_digits=9, decimal_places=6)
    geo_center_lng = models.DecimalField(max_digits=9, decimal_places=6)
    radius_km = models.DecimalField(max_digits=6, decimal_places=2)


class CaregiverAvailability(BaseModel):
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='availabilities')
    weekday = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(6)])
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_recurring = models.BooleanField(default=True)

    class Meta:
        ordering = ['weekday', 'start_time']


class TimeOff(BaseModel):
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='time_off')
    date_from = models.DateField()
    date_to = models.DateField()
    reason = models.TextField(blank=True)


class Booking(TimestampedModel):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    PAYMENT_PENDING = 'pending'
    PAYMENT_PAID = 'paid'
    PAYMENT_REFUNDED = 'refunded'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_PAID, 'Paid'),
        (PAYMENT_REFUNDED, 'Refunded'),
    ]

    owner = models.ForeignKey(OwnerProfile, on_delete=models.CASCADE, related_name='bookings')
    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='bookings')
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='bookings')
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, related_name='bookings')
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    owner_notes = models.TextField(blank=True)
    caregiver_notes = models.TextField(blank=True)
    price_subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    caregiver_earnings = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_PENDING)

    class Meta:
        indexes = [models.Index(fields=['status', 'start_datetime'])]

    ALLOWED_TRANSITIONS = {
        STATUS_PENDING: {STATUS_ACCEPTED, STATUS_REJECTED, STATUS_CANCELLED},
        STATUS_ACCEPTED: {STATUS_COMPLETED, STATUS_CANCELLED},
    }

    def change_status(self, new_status: str) -> None:
        """Enforce finite state machine for booking statuses."""
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(f"Invalid transition from {self.status} to {new_status}")
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])

    @transaction.atomic
    def mark_paid(self) -> None:
        if self.payment_status == self.PAYMENT_PAID:
            return
        self.payment_status = self.PAYMENT_PAID
        self.save(update_fields=['payment_status', 'updated_at'])
        TransactionLog.objects.create(
            booking=self,
            user=self.caregiver.user,
            direction=TransactionLog.DIRECTION_CREDIT,
            amount=self.caregiver_earnings,
            description='Booking payout',
        )


class BookingRecurringRule(BaseModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='recurring_rules')
    recurrence_type = models.CharField(max_length=50, default='weekly')
    weekdays = ArrayField(models.IntegerField(), blank=True, default=list)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


class WalkSession(TimestampedModel):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='walk_sessions')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    distance_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    route_geojson = models.JSONField(default=list)
    pee_events = models.PositiveIntegerField(default=0)
    poo_events = models.PositiveIntegerField(default=0)
    food_given = models.BooleanField(default=False)
    water_given = models.BooleanField(default=False)
    notes = models.TextField(blank=True)


class WalkPhoto(TimestampedModel):
    session = models.ForeignKey(WalkSession, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='walk_photos/')


class Review(TimestampedModel):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews_written')
    target_caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.target_caregiver:
            self.target_caregiver.recalc_ratings()


class Payout(TimestampedModel):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
    ]

    caregiver = models.ForeignKey(CaregiverProfile, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=5, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    paid_at = models.DateTimeField(null=True, blank=True)


class TransactionLog(TimestampedModel):
    DIRECTION_CREDIT = 'credit'
    DIRECTION_DEBIT = 'debit'
    DIRECTIONS = [
        (DIRECTION_CREDIT, 'Credit'),
        (DIRECTION_DEBIT, 'Debit'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    direction = models.CharField(max_length=10, choices=DIRECTIONS)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()


# Utility functions


def is_caregiver_available(
    caregiver: CaregiverProfile,
    start: timezone.datetime,
    end: timezone.datetime,
) -> bool:
    """Check recurring availability, time off, and overlapping bookings."""
    weekday = start.weekday()
    time_range_ok = caregiver.availabilities.filter(
        weekday=weekday,
        start_time__lte=start.time(),
        end_time__gte=end.time(),
    ).exists()
    if not time_range_ok:
        return False

    if caregiver.time_off.filter(date_from__lte=start.date(), date_to__gte=end.date()).exists():
        return False

    overlapping = caregiver.bookings.filter(
        status__in=[Booking.STATUS_PENDING, Booking.STATUS_ACCEPTED],
        start_datetime__lt=end,
        end_datetime__gt=start,
    ).exists()
    return not overlapping


def compute_commission(amount: Decimal) -> tuple[Decimal, Decimal]:
    platform_fee = (amount * settings.PLATFORM_FEE_PERCENT).quantize(Decimal('0.01'))
    caregiver_earnings = amount - platform_fee
    return platform_fee, caregiver_earnings
