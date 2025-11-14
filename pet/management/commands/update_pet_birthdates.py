from django.core.management.base import BaseCommand
from pet.models import Pet

class Command(BaseCommand):
    help = 'Update birth_date for all existing pets based on their age_years, age_months, and age_weeks'

    def handle(self, *args, **options):
        pets = Pet.objects.all()
        updated_count = 0
        
        for pet in pets:
            # Only update if birth_date is not set but age fields are
            if not pet.birth_date and any([pet.age_years, pet.age_months, pet.age_weeks]):
                pet.birth_date = pet.calculate_birth_date_from_age()
                pet.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated birth_date for pet: {pet.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal pets updated: {updated_count}')
        )
