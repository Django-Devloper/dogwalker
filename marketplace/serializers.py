"""Serializers for the marketplace API."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Booking,
    CaregiverAvailability,
    CaregiverProfile,
    CaregiverService,
    OwnerProfile,
    Pet,
    Review,
    ServiceType,
    WalkPhoto,
    WalkSession,
    Payout,
    TransactionLog,
    is_caregiver_available,
    compute_commission,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class OwnerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = OwnerProfile
        fields = ['id', 'user', 'phone', 'country', 'city', 'address_line1', 'address_line2', 'postal_code']


class CaregiverProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = CaregiverProfile
        fields = [
            'id',
            'user',
            'phone',
            'city',
            'bio',
            'years_experience',
            'hourly_rate_base',
            'services_offered',
            'max_pets',
            'accepts_large_dogs',
            'accepts_aggressive',
            'verified',
            'rating_average',
            'rating_count',
            'gps_radius_km',
        ]


class PetSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Pet
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner']


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = ['id', 'code', 'name', 'description', 'base_duration_minutes', 'default_base_price']


class CaregiverServiceSerializer(serializers.ModelSerializer):
    service_type = ServiceTypeSerializer(read_only=True)

    class Meta:
        model = CaregiverService
        fields = ['id', 'service_type', 'price_per_unit', 'is_active']


class CaregiverListSerializer(serializers.ModelSerializer):
    services = CaregiverServiceSerializer(many=True, read_only=True)

    class Meta:
        model = CaregiverProfile
        fields = [
            'id',
            'user',
            'city',
            'services',
            'rating_average',
            'rating_count',
            'accepts_large_dogs',
        ]


class CaregiverDetailSerializer(CaregiverProfileSerializer):
    services = CaregiverServiceSerializer(many=True, read_only=True)
    availabilities = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    class Meta(CaregiverProfileSerializer.Meta):
        fields = CaregiverProfileSerializer.Meta.fields + ['services', 'availabilities', 'reviews']

    def get_availabilities(self, obj: CaregiverProfile):
        qs = obj.availabilities.all()
        return [
            {
                'weekday': a.weekday,
                'start_time': a.start_time,
                'end_time': a.end_time,
            }
            for a in qs
        ]

    def get_reviews(self, obj: CaregiverProfile):
        reviews = obj.reviews.select_related('author').all()[:10]
        return [
            {
                'rating': r.rating,
                'comment': r.comment,
                'author': r.author.username,
                'created_at': r.created_at,
            }
            for r in reviews
        ]


class BookingCreateSerializer(serializers.ModelSerializer):
    pet_id = serializers.UUIDField(write_only=True)
    caregiver_id = serializers.UUIDField(write_only=True)
    service_type_code = serializers.SlugField(write_only=True)
    owner_notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Booking
        fields = [
            'id',
            'pet_id',
            'caregiver_id',
            'service_type_code',
            'start_datetime',
            'duration_minutes',
            'owner_notes',
        ]
        read_only_fields = ['id']

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = self.context['request'].user
        try:
            owner = user.ownerprofile
        except OwnerProfile.DoesNotExist as exc:
            raise serializers.ValidationError('Only owners can create bookings') from exc

        try:
            pet = owner.pets.get(id=attrs['pet_id'])
        except Pet.DoesNotExist as exc:
            raise serializers.ValidationError('Pet not found') from exc

        try:
            caregiver = CaregiverProfile.objects.get(id=attrs['caregiver_id'])
        except CaregiverProfile.DoesNotExist as exc:
            raise serializers.ValidationError('Caregiver not found') from exc

        try:
            service_type = ServiceType.objects.get(code=attrs['service_type_code'])
        except ServiceType.DoesNotExist as exc:
            raise serializers.ValidationError('Service type not found') from exc

        try:
            caregiver_service = CaregiverService.objects.get(
                caregiver=caregiver, service_type=service_type, is_active=True
            )
        except CaregiverService.DoesNotExist as exc:
            raise serializers.ValidationError('Caregiver does not offer this service') from exc

        start: timezone.datetime = attrs['start_datetime']
        duration = attrs['duration_minutes']
        end = start + timezone.timedelta(minutes=duration)

        if start < timezone.now():
            raise serializers.ValidationError('Start time must be in the future')

        if duration > service_type.base_duration_minutes * 4:
            raise serializers.ValidationError('Duration exceeds allowed maximum for service type')

        if not is_caregiver_available(caregiver, start, end):
            raise serializers.ValidationError('Caregiver is not available for the selected time')

        platform_fee, caregiver_earnings = compute_commission(caregiver_service.price_per_unit)
        attrs.update(
            {
                'owner': owner,
                'pet': pet,
                'caregiver': caregiver,
                'service_type': service_type,
                'end_datetime': end,
                'price_subtotal': caregiver_service.price_per_unit,
                'platform_fee': platform_fee,
                'caregiver_earnings': caregiver_earnings,
            }
        )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Booking:
        validated_data.pop('pet_id', None)
        validated_data.pop('caregiver_id', None)
        validated_data.pop('service_type_code', None)
        return super().create(validated_data)


class BookingDetailSerializer(serializers.ModelSerializer):
    owner = OwnerProfileSerializer(read_only=True)
    caregiver = CaregiverProfileSerializer(read_only=True)
    pet = PetSerializer(read_only=True)
    service_type = ServiceTypeSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'


class BookingStatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class WalkPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalkPhoto
        fields = ['id', 'image', 'created_at']
        read_only_fields = ['id', 'created_at']


class WalkSessionSerializer(serializers.ModelSerializer):
    photos = WalkPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = WalkSession
        fields = [
            'id',
            'booking',
            'started_at',
            'ended_at',
            'distance_meters',
            'route_geojson',
            'pee_events',
            'poo_events',
            'food_given',
            'water_given',
            'notes',
            'photos',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReviewSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'booking', 'author', 'target_caregiver', 'rating', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'target_caregiver', 'created_at', 'updated_at']

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        booking: Booking = attrs['booking']
        if booking.status != Booking.STATUS_COMPLETED:
            raise serializers.ValidationError('Reviews are only allowed for completed bookings')
        if hasattr(booking, 'review'):
            raise serializers.ValidationError('A review already exists for this booking')
        attrs['target_caregiver'] = booking.caregiver
        return attrs

    def create(self, validated_data: dict[str, Any]) -> Review:
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = ['id', 'amount', 'currency', 'status', 'paid_at', 'created_at']
        read_only_fields = ['id', 'created_at']


class FinanceSummarySerializer(serializers.Serializer):
    total_earnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    upcoming_payouts = serializers.DecimalField(max_digits=12, decimal_places=2)
    last_30_days = serializers.DecimalField(max_digits=12, decimal_places=2)


class TransactionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionLog
        fields = ['id', 'booking', 'direction', 'amount', 'description', 'created_at']
