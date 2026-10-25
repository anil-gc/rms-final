from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import LoginRateLimit


class Command(BaseCommand):
    help = "Remove expired login-limit buckets older than one day; schedule daily."

    def handle(self, *args, **options):
        count, _ = LoginRateLimit.objects.filter(
            window_started__lt=timezone.now() - timedelta(days=1)
        ).delete()
        self.stdout.write(f"Removed {count} expired login-limit buckets.")
