"""URL patterns for template-powered frontend pages."""
from django.urls import path

from .frontend import LandingPageView, CaregiverDirectoryView

urlpatterns = [
    path('', LandingPageView.as_view(), name='home'),
    path('caregivers/', CaregiverDirectoryView.as_view(), name='caregiver-directory'),
]
