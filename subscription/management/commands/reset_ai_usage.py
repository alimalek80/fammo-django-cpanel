from django.core.management.base import BaseCommand
from subscription.models import AIUsage
from subscription.models import first_day_of_current_month

class Command(BaseCommand):
    help = "Reset AI usage for all users monthly"

    def handle(self, *args, **options):
        today = first_day_of_current_month()
        count = 0

        for usage in AIUsage.objects.all():
            if usage.is_reset_needed():
                usage.reset()
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Reset {count} usage records."))
