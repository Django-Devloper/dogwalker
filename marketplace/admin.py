from django.contrib import admin

from .models import (
    OwnerProfile,
    CaregiverProfile,
    Pet,
    ServiceType,
    CaregiverService,
    ServiceArea,
    CaregiverAvailability,
    TimeOff,
    Booking,
    BookingRecurringRule,
    WalkSession,
    WalkPhoto,
    Review,
    Payout,
    TransactionLog,
)


@admin.register(OwnerProfile)
class OwnerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'country')
    search_fields = ('user__username', 'city')


class CaregiverServiceInline(admin.TabularInline):
    model = CaregiverService
    extra = 1


@admin.register(CaregiverProfile)
class CaregiverProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'verified', 'rating_average', 'rating_count')
    list_filter = ('city', 'verified')
    search_fields = ('user__username', 'city')
    inlines = [CaregiverServiceInline]


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'owner')
    search_fields = ('name', 'owner__user__username')


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'base_duration_minutes')
    search_fields = ('code', 'name')


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):
    list_display = ('caregiver', 'city', 'country', 'radius_km')
    list_filter = ('city', 'country')


@admin.register(CaregiverAvailability)
class CaregiverAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('caregiver', 'weekday', 'start_time', 'end_time', 'is_recurring')
    list_filter = ('weekday',)


@admin.register(TimeOff)
class TimeOffAdmin(admin.ModelAdmin):
    list_display = ('caregiver', 'date_from', 'date_to', 'reason')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('owner', 'caregiver', 'service_type', 'start_datetime', 'status', 'payment_status')
    list_filter = ('status', 'payment_status', 'service_type')
    search_fields = ('owner__user__username', 'caregiver__user__username')


@admin.register(BookingRecurringRule)
class BookingRecurringRuleAdmin(admin.ModelAdmin):
    list_display = ('booking', 'recurrence_type', 'is_active')


@admin.register(WalkSession)
class WalkSessionAdmin(admin.ModelAdmin):
    list_display = ('booking', 'started_at', 'ended_at', 'distance_meters')


@admin.register(WalkPhoto)
class WalkPhotoAdmin(admin.ModelAdmin):
    list_display = ('session', 'created_at')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('booking', 'rating', 'author', 'target_caregiver')
    list_filter = ('rating',)


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('caregiver', 'amount', 'currency', 'status', 'paid_at')
    list_filter = ('status',)


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ('booking', 'user', 'direction', 'amount', 'created_at')
    list_filter = ('direction',)
