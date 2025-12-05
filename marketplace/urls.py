from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterOwnerView,
    RegisterCaregiverView,
    login_view,
    MeView,
    PetViewSet,
    CaregiverViewSet,
    BookingViewSet,
    WalkSessionViewSet,
    ReviewViewSet,
    PayoutViewSet,
    FinanceSummaryView,
)

router = DefaultRouter()
router.register(r'pets', PetViewSet, basename='pet')
router.register(r'caregivers', CaregiverViewSet, basename='caregiver')
router.register(r'bookings', BookingViewSet, basename='booking')
router.register(r'walks', WalkSessionViewSet, basename='walk')
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'payouts', PayoutViewSet, basename='payout')

urlpatterns = [
    path('auth/register/owner/', RegisterOwnerView.as_view(), name='register-owner'),
    path('auth/register/caregiver/', RegisterCaregiverView.as_view(), name='register-caregiver'),
    path('auth/login/', login_view, name='login'),
    path('me/', MeView.as_view(), name='me'),
    path('finance/summary/', FinanceSummaryView.as_view(), name='finance-summary'),
    path('', include(router.urls)),
]
