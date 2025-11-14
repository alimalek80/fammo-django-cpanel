from django.core.management.base import BaseCommand
from vets.models import Clinic, ReferralCode


class Command(BaseCommand):
    help = 'Create referral codes for email-confirmed clinics that do not have them'

    def handle(self, *args, **options):
        # Find email-confirmed clinics without active referral codes
        clinics_without_codes = []
        
        for clinic in Clinic.objects.filter(email_confirmed=True):
            if not clinic.referral_codes.filter(is_active=True).exists():
                clinics_without_codes.append(clinic)
        
        if not clinics_without_codes:
            self.stdout.write(
                self.style.SUCCESS(
                    'All email-confirmed clinics already have referral codes.'
                )
            )
            return
        
        # Create referral codes for these clinics
        created_count = 0
        for clinic in clinics_without_codes:
            try:
                ReferralCode.create_default_for_clinic(clinic)
                created_count += 1
                self.stdout.write(
                    f'Created referral code for clinic: {clinic.name}'
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to create referral code for {clinic.name}: {e}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} referral codes for email-confirmed clinics.'
            )
        )