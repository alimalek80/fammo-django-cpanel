from django.db import models
from django.conf import settings

class PetType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class Gender(models.Model):
    name = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def __str__(self):
        return self.name
    
class AgeCategory(models.Model):
    name = models.CharField(max_length=50)
    pet_type = models.ForeignKey(PetType, on_delete=models.CASCADE, related_name='age_categories')
    order = models.PositiveIntegerField(default=0, help_text="Controls display order (smallest first)")

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} ({self.pet_type.name})"
    
class Breed(models.Model):
    pet_type = models.ForeignKey(PetType, on_delete=models.CASCADE, related_name='breeds')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.pet_type.name})"
    
class FoodType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
    
class FoodFeeling(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=255)

    def __str__(self):
        return self.name

class FoodImportance(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class BodyType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=255)

    def __str__(self):
        return self.name
    
class ActivityLevel(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)  # Add this field

    class Meta:
        ordering = ['order', 'name']  # Default ordering

    def __str__(self):
        return self.name

class FoodAllergy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0)  # Add this

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
    
class HealthIssue(models.Model):
    name = models.CharField(max_length=100, unique=True)
    order = models.PositiveIntegerField(default=0)  # Add this

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

class TreatFrequency(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Pet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    pet_type = models.ForeignKey(PetType, on_delete=models.SET_NULL, null=True, blank=True, related_name='pets')
    gender = models.ForeignKey(Gender, on_delete=models.SET_NULL, null=True, blank=True)
    neutered = models.BooleanField(null=True, blank=True)
    age_category = models.ForeignKey('AgeCategory', on_delete=models.SET_NULL, null=True, blank=True)
    age_years = models.PositiveIntegerField(null=True, blank=True)
    age_months = models.PositiveIntegerField(null=True, blank=True)
    age_weeks = models.PositiveIntegerField(null=True, blank=True)
    breed = models.ForeignKey(Breed, on_delete=models.SET_NULL, null=True, blank=True, related_name='pets')
    unknown_breed = models.BooleanField(default=False, help_text="Check if breed is unknown")
    food_types = models.ManyToManyField(FoodType, blank=True, related_name='pets')
    food_feeling = models.ForeignKey(FoodFeeling, on_delete=models.SET_NULL, null=True, blank=True, related_name='pets')
    food_importance = models.ForeignKey(FoodImportance, on_delete=models.SET_NULL, null=True, blank=True, related_name='pets')
    body_type = models.ForeignKey(BodyType, on_delete=models.SET_NULL, null=True, blank=True, related_name='pets')
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    activity_level = models.ForeignKey(ActivityLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name='pets')
    food_allergies = models.ManyToManyField('FoodAllergy', blank=True, related_name='pets')
    food_allergy_other = models.CharField(max_length=255, blank=True, null=True)
    health_issues = models.ManyToManyField('HealthIssue', blank=True, related_name='pets')
    treat_frequency = models.ForeignKey('TreatFrequency', on_delete=models.SET_NULL, null=True, blank=True, related_name='pets')

    @property
    def total_age_in_days(self):
        # Optional utility to calculate pet's total age in days
        days = 0
        if self.age_years:
            days += self.age_years * 365
        if self.age_months:
            days += self.age_months * 30
        if self.age_weeks:
            days += self.age_weeks * 7
        return days

    def __str__(self):
        return f"{self.name} ({self.user.email})"
    
    def get_full_profile_for_ai(self):
        """Return a detailed, human-readable string of all pet info for AI prompts."""
        profile = [
            f"Name: {self.name}",
            f"Species: {self.pet_type.name if self.pet_type else 'N/A'}",
            f"Breed: {self.breed.name if self.breed else 'N/A'}",
            f"Gender: {self.gender.name if self.gender else 'N/A'}",
            f"Neutered: {'Yes' if self.neutered else 'No'}",
            f"Age: {self.age_years or 0} years, {self.age_months or 0} months, {self.age_weeks or 0} weeks",
            f"Age Category: {self.age_category.name if self.age_category else 'N/A'}",
            f"Weight: {self.weight or 'N/A'} kg",
            f"Body Type: {self.body_type.name if self.body_type else 'N/A'}",
            f"Activity Level: {self.activity_level.name if self.activity_level else 'N/A'}",
            f"Food Types: {', '.join([ft.name for ft in self.food_types.all()]) or 'None'}",
            f"Food Feeling: {self.food_feeling.name if self.food_feeling else 'N/A'}",
            f"Food Importance: {self.food_importance.name if self.food_importance else 'N/A'}",
            f"Treat Frequency: {self.treat_frequency.name if self.treat_frequency else 'N/A'}",
            f"Health Issues: {', '.join([hi.name for hi in self.health_issues.all()]) or 'None'}",
            f"Food Allergies: {', '.join([fa.name for fa in self.food_allergies.all()]) or 'None'}",
            f"Other Food Allergy: {self.food_allergy_other or 'None'}",
        ]
        return "\n".join(profile)







