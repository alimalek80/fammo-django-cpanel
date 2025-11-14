"""
Management command to geocode existing clinics that don't have coordinates.
Usage: python manage.py geocode_clinics [--all] [--force]
"""
from django.core.management.base import BaseCommand
from vets.models import Clinic
from vets.utils import geocode_address
import time


class Command(BaseCommand):
    help = 'Geocode clinic addresses to get latitude/longitude coordinates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all clinics, even those with coordinates',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-geocode even if coordinates exist',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of clinics to process',
        )

    def handle(self, *args, **options):
        # Build queryset
        if options['force']:
            clinics = Clinic.objects.all()
            self.stdout.write(self.style.WARNING('Force mode: Re-geocoding ALL clinics'))
        else:
            clinics = Clinic.objects.filter(
                latitude__isnull=True,
            ) | Clinic.objects.filter(
                longitude__isnull=True,
            )
            self.stdout.write(f'Processing clinics without coordinates')
        
        # Apply limit
        if options['limit']:
            clinics = clinics[:options['limit']]
        
        total = clinics.count()
        self.stdout.write(f'Found {total} clinic(s) to process\n')
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ All clinics already have coordinates!'))
            return
        
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        for i, clinic in enumerate(clinics, 1):
            # Skip if no address info
            if not clinic.address and not clinic.city:
                self.stdout.write(
                    self.style.WARNING(f'[{i}/{total}] ⊘ {clinic.name}: No address or city')
                )
                skip_count += 1
                continue
            
            self.stdout.write(f'[{i}/{total}] Processing: {clinic.name}')
            
            try:
                # Build address string
                full_address = f"{clinic.address}, {clinic.city}" if clinic.address and clinic.city else (clinic.address or clinic.city)
                self.stdout.write(f'  Address: {full_address}')
                
                # Geocode
                coords = geocode_address(clinic.address, clinic.city)
                
                if coords:
                    lat, lng = coords
                    clinic.latitude = lat
                    clinic.longitude = lng
                    clinic.save(update_fields=['latitude', 'longitude'])
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Success: {lat:.6f}, {lng:.6f}')
                    )
                    success_count += 1
                else:
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Failed: Could not geocode address')
                    )
                    fail_count += 1
                
                # Rate limiting (Nominatim requires 1 request per second)
                if i < total:
                    time.sleep(1.1)
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error: {str(e)}')
                )
                fail_count += 1
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully geocoded: {success_count}'))
        if fail_count:
            self.stdout.write(self.style.ERROR(f'✗ Failed: {fail_count}'))
        if skip_count:
            self.stdout.write(self.style.WARNING(f'⊘ Skipped (no address): {skip_count}'))
        self.stdout.write('='*50)
