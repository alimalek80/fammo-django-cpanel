from django.contrib import admin
from .models import Pet, PetType, Gender, AgeCategory, Breed, FoodType, FoodFeeling, FoodImportance, BodyType, ActivityLevel, FoodAllergy, HealthIssue, TreatFrequency

class ActivityLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    ordering = ('order', 'name')

class FoodAllergyAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    ordering = ('order', 'name')

class HealthIssueAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
    ordering = ('order', 'name')

class AgeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'pet_type', 'order')
    list_editable = ('order',)
    ordering = ('pet_type', 'order', 'name')

admin.site.register(Pet)
admin.site.register(PetType)
admin.site.register(Gender)
admin.site.register(AgeCategory, AgeCategoryAdmin)
admin.site.register(Breed)
admin.site.register(FoodType)
admin.site.register(FoodFeeling)
admin.site.register(FoodImportance)
admin.site.register(BodyType)
admin.site.register(ActivityLevel, ActivityLevelAdmin)
admin.site.register(FoodAllergy, FoodAllergyAdmin)
admin.site.register(HealthIssue, HealthIssueAdmin)
admin.site.register(TreatFrequency)



