"""API views for the pet care marketplace."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework import generics, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import (
    Booking,
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
)
from .serializers import (
    BookingCreateSerializer,
    BookingDetailSerializer,
    CaregiverDetailSerializer,
    CaregiverListSerializer,
    CaregiverProfileSerializer,
    OwnerProfileSerializer,
    PetSerializer,
    ReviewSerializer,
    WalkPhotoSerializer,
    WalkSessionSerializer,
    PayoutSerializer,
    FinanceSummarySerializer,
    TransactionLogSerializer,
)


class RegisterOwnerView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = OwnerProfileSerializer

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            user = User.objects.create_user(
                username=request.data.get('username'),
                email=request.data.get('email'),
                password=request.data.get('password'),
            )
            profile = OwnerProfile.objects.create(
                user=user,
                phone=request.data.get('phone', ''),
                country=request.data.get('country', ''),
                city=request.data.get('city', ''),
                address_line1=request.data.get('address_line1', ''),
                address_line2=request.data.get('address_line2', ''),
                postal_code=request.data.get('postal_code', ''),
            )
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RegisterCaregiverView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CaregiverProfileSerializer

    def create(self, request, *args, **kwargs):
        with transaction.atomic():
            user = User.objects.create_user(
                username=request.data.get('username'),
                email=request.data.get('email'),
                password=request.data.get('password'),
            )
            profile = CaregiverProfile.objects.create(
                user=user,
                phone=request.data.get('phone', ''),
                city=request.data.get('city', ''),
                bio=request.data.get('bio', ''),
                years_experience=request.data.get('years_experience', 0),
                hourly_rate_base=request.data.get('hourly_rate_base', Decimal('0.00')),
                services_offered=request.data.get('services_offered', []),
                max_pets=request.data.get('max_pets', 1),
                accepts_large_dogs=request.data.get('accepts_large_dogs', False),
                accepts_aggressive=request.data.get('accepts_aggressive', False),
                gps_radius_km=request.data.get('gps_radius_km', Decimal('0.00')),
            )
        serializer = self.get_serializer(profile)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    user = authenticate(username=request.data.get('username'), password=request.data.get('password'))
    if not user:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key})


class MeView(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        data = {'user': User.objects.get(pk=request.user.pk).username}
        try:
            data['owner_profile'] = OwnerProfileSerializer(request.user.ownerprofile).data
        except OwnerProfile.DoesNotExist:
            data['owner_profile'] = None
        try:
            data['caregiver_profile'] = CaregiverProfileSerializer(request.user.caregiverprofile).data
        except CaregiverProfile.DoesNotExist:
            data['caregiver_profile'] = None
        return Response(data)


class PetViewSet(viewsets.ModelViewSet):
    serializer_class = PetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Pet.objects.filter(owner__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user.ownerprofile)


class CaregiverViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CaregiverProfile.objects.all().prefetch_related('services')
    serializer_class = CaregiverListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['city', 'accepts_large_dogs']
    search_fields = ['user__username', 'city']
    ordering_fields = ['rating_average', 'services__price_per_unit']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CaregiverDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        qs = super().get_queryset()
        service_type = self.request.query_params.get('service_type')
        min_rating = self.request.query_params.get('min_rating')
        price_min = self.request.query_params.get('price_min')
        price_max = self.request.query_params.get('price_max')
        if service_type:
            qs = qs.filter(services__service_type__code=service_type, services__is_active=True)
        if min_rating:
            qs = qs.filter(rating_average__gte=Decimal(min_rating))
        if price_min:
            qs = qs.filter(services__price_per_unit__gte=Decimal(price_min))
        if price_max:
            qs = qs.filter(services__price_per_unit__lte=Decimal(price_max))
        return qs.distinct()


class BookingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Booking.objects.select_related('owner', 'caregiver', 'pet', 'service_type')

    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        as_caregiver = self.request.query_params.get('as') == 'caregiver'
        if as_caregiver:
            qs = qs.filter(caregiver__user=self.request.user)
        else:
            qs = qs.filter(owner__user=self.request.user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        booking = self.get_object()
        if booking.caregiver.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        booking.change_status(Booking.STATUS_ACCEPTED)
        return Response({'status': booking.status})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        booking = self.get_object()
        if booking.caregiver.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        booking.change_status(Booking.STATUS_REJECTED)
        return Response({'status': booking.status})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if request.user not in (booking.owner.user, booking.caregiver.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        booking.change_status(Booking.STATUS_CANCELLED)
        return Response({'status': booking.status})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        booking = self.get_object()
        if booking.caregiver.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        booking.change_status(Booking.STATUS_COMPLETED)
        return Response({'status': booking.status})


class WalkSessionViewSet(viewsets.ModelViewSet):
    serializer_class = WalkSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WalkSession.objects.filter(booking__caregiver__user=self.request.user)

    def perform_create(self, serializer):
        booking = serializer.validated_data['booking']
        if booking.caregiver.user != self.request.user:
            raise permissions.PermissionDenied('Not your booking')
        serializer.save()

    @action(detail=True, methods=['post'])
    def photos(self, request, pk=None):
        session = self.get_object()
        serializer = WalkPhotoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(session=session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        caregiver_id = self.request.query_params.get('caregiver')
        qs = Review.objects.all()
        if caregiver_id:
            qs = qs.filter(target_caregiver_id=caregiver_id)
        return qs


class PayoutViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayoutSerializer

    def get_queryset(self):
        return Payout.objects.filter(caregiver__user=self.request.user)


class FinanceSummaryView(generics.GenericAPIView):
    serializer_class = FinanceSummarySerializer

    def get(self, request, *args, **kwargs):
        caregiver = request.user.caregiverprofile
        total_earnings = (
            TransactionLog.objects.filter(user=request.user, direction=TransactionLog.DIRECTION_CREDIT)
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        upcoming_payouts = (
            Payout.objects.filter(caregiver=caregiver, status__in=[Payout.STATUS_PENDING, Payout.STATUS_PROCESSING])
            .aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        last_30_days = (
            TransactionLog.objects.filter(
                user=request.user,
                direction=TransactionLog.DIRECTION_CREDIT,
                created_at__gte=timezone.now() - timedelta(days=30),
            ).aggregate(total=Sum('amount'))['total']
            or Decimal('0.00')
        )
        serializer = self.get_serializer(
            {'total_earnings': total_earnings, 'upcoming_payouts': upcoming_payouts, 'last_30_days': last_30_days}
        )
        return Response(serializer.data)
