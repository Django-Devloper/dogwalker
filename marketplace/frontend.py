"""Template-based frontend views for the marketplace."""
from __future__ import annotations

from decimal import Decimal
from django.views.generic import TemplateView, ListView

from .models import CaregiverProfile, ServiceType, Booking


class LandingPageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'caregiver_count': CaregiverProfile.objects.count(),
                'service_type_count': ServiceType.objects.count(),
                'active_city_count': CaregiverProfile.objects.exclude(city='').values('city').distinct().count(),
                'recent_reviews_count': Booking.objects.filter(status=Booking.STATUS_COMPLETED).count(),
                'top_caregivers': CaregiverProfile.objects.order_by('-rating_average')[:3],
                'service_types': ServiceType.objects.order_by('name'),
            }
        )
        return context


class CaregiverDirectoryView(ListView):
    template_name = 'caregivers.html'
    context_object_name = 'caregivers'
    model = CaregiverProfile

    def get_queryset(self):
        queryset = (
            CaregiverProfile.objects.prefetch_related('services__service_type', 'user')
            .order_by('-rating_average', '-rating_count')
        )
        city = self.request.GET.get('city')
        service_type = self.request.GET.get('service_type')
        min_rating = self.request.GET.get('min_rating')
        accepts_large_dogs = self.request.GET.get('accepts_large_dogs')
        if city:
            queryset = queryset.filter(city__icontains=city)
        if service_type:
            queryset = queryset.filter(services__service_type__code=service_type, services__is_active=True)
        if min_rating:
            try:
                queryset = queryset.filter(rating_average__gte=Decimal(min_rating))
            except Exception:
                pass
        if accepts_large_dogs:
            queryset = queryset.filter(accepts_large_dogs=True)
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service_types'] = ServiceType.objects.order_by('name')
        return context
