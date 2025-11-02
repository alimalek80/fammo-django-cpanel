from django.core.management.base import BaseCommand
from userapp.models import CustomUser, Profile
from pet.models import Pet, PetType, Gender, Breed, AgeCategory, BodyType, ActivityLevel, FoodType, FoodFeeling, FoodImportance, TreatFrequency
from decimal import Decimal
from django.db import transaction
from datetime import datetime
from django.utils import timezone
import csv
import os


class Command(BaseCommand):
    help = 'Create sample users with profiles and pet profiles from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='userapp/fammo_users_realistic_part4.csv',
            help='Path to CSV file (relative to project root)'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        
        # Make path absolute if it's relative
        if not os.path.isabs(csv_path):
            from django.conf import settings
            csv_path = os.path.join(settings.BASE_DIR, csv_path)
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return
        
        created_count = 0
        skipped_count = 0
        pets_created = 0
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f'[START] Importing users from CSV: {csv_path}'))
        self.stdout.write("="*60 + "\n")
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    email = row['email']
                    
                    # Check if user already exists
                    if CustomUser.objects.filter(email=email).exists():
                        self.stdout.write(self.style.WARNING(f"[SKIP] User {email} already exists. Skipping..."))
                        skipped_count += 1
                        continue
                    
                    try:
                        with transaction.atomic():
                            # Parse date_joined
                            date_joined_str = row['date_joined']
                            date_joined = datetime.fromisoformat(date_joined_str.replace('Z', '+00:00'))
                            if timezone.is_naive(date_joined):
                                date_joined = timezone.make_aware(date_joined)
                            
                            # Create the user
                            user = CustomUser.objects.create_user(
                                email=email,
                                password=row['password'],
                                date_joined=date_joined,
                                is_active=True
                            )
                            
                            # Update the profile (created automatically by signal)
                            profile = user.profile
                            profile.first_name = row['first_name']
                            profile.last_name = row['last_name']
                            profile.phone = row['phone']
                            profile.address = row['address']
                            profile.city = row['city']
                            profile.zip_code = row['zip_code']
                            profile.country = row['country']
                            profile.save()
                            
                            self.stdout.write(self.style.SUCCESS(
                                f"[OK] Created user: {row['first_name']} {row['last_name']} ({email})"
                            ))
                            created_count += 1
                            
                            # Create pet profile if pet data exists
                            if row.get('pet_name') and row['pet_name'].strip():
                                try:
                                    # Get or create related objects
                                    pet_type, _ = PetType.objects.get_or_create(name=row['pet_type'])
                                    gender, _ = Gender.objects.get_or_create(name=row['pet_gender'])
                                    breed, _ = Breed.objects.get_or_create(
                                        name=row['pet_breed'],
                                        pet_type=pet_type
                                    )
                                    body_type, _ = BodyType.objects.get_or_create(
                                        name=row['pet_body_type'],
                                        defaults={'description': f'{row["pet_body_type"]} body type'}
                                    )
                                    activity_level, _ = ActivityLevel.objects.get_or_create(
                                        name=row['pet_activity_level'],
                                        defaults={'description': f'{row["pet_activity_level"]} activity level'}
                                    )
                                    food_feeling, _ = FoodFeeling.objects.get_or_create(
                                        name=row['pet_food_feeling'],
                                        defaults={'description': row['pet_food_feeling']}
                                    )
                                    food_importance, _ = FoodImportance.objects.get_or_create(
                                        name=row['pet_food_importance']
                                    )
                                    
                                    # Create the pet
                                    pet = Pet.objects.create(
                                        user=user,
                                        name=row['pet_name'],
                                        pet_type=pet_type,
                                        gender=gender,
                                        breed=breed,
                                        neutered=row['pet_neutered'].lower() in ['true', '1', 'yes'],
                                        age_years=int(float(row['pet_age_years'])) if row['pet_age_years'] else 0,
                                        age_months=int(float(row['pet_age_months'])) if row['pet_age_months'] else 0,
                                        weight=Decimal(row['pet_weight']),
                                        body_type=body_type,
                                        activity_level=activity_level,
                                        food_feeling=food_feeling,
                                        food_importance=food_importance
                                    )
                                    
                                    # Add food types (can be comma-separated)
                                    food_types_str = row['pet_food_types']
                                    if food_types_str:
                                        food_type_names = [ft.strip() for ft in food_types_str.split(',')]
                                        for food_type_name in food_type_names:
                                            if food_type_name:
                                                food_type, _ = FoodType.objects.get_or_create(name=food_type_name)
                                                pet.food_types.add(food_type)
                                    
                                    self.stdout.write(self.style.SUCCESS(
                                        f"  └─ Created pet: {row['pet_name']} ({row['pet_type']})"
                                    ))
                                    pets_created += 1
                                    
                                except Exception as pet_error:
                                    self.stdout.write(self.style.ERROR(
                                        f"  └─ [ERROR] Failed to create pet: {str(pet_error)}"
                                    ))
                                    raise  # Re-raise to rollback the transaction
                            
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"[ERROR] Error creating user {email}: {str(e)}"))
                        skipped_count += 1
        
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {str(e)}"))
            return
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"Successfully created: {created_count} users"))
        self.stdout.write(self.style.SUCCESS(f"Successfully created: {pets_created} pets"))
        self.stdout.write(self.style.WARNING(f"Skipped: {skipped_count} users"))
        self.stdout.write("="*60)
        self.stdout.write(self.style.NOTICE(f"\nImported from: {csv_path}\n"))