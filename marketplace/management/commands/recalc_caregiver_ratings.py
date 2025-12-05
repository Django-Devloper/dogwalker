from django.core.management.base import BaseCommand

from marketplace.models import CaregiverProfile


class Command(BaseCommand):
    help = 'Recalculate caregiver rating aggregates based on reviews.'

    def handle(self, *args, **options):
        for caregiver in CaregiverProfile.objects.all():
            caregiver.recalc_ratings()
            self.stdout.write(self.style.SUCCESS(f'Updated {caregiver.user.username}'))
