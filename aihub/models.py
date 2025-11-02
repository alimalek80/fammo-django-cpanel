from django.db import models
from pet.models import Pet
from django.utils.translation import gettext_lazy as _

class RecommendationType(models.TextChoices):
    MEAL = 'meal', _('Meal')
    HEALTH = 'health', _('Health')

class AIRecommendation(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='ai_recommendations')
    type = models.CharField(max_length=20, choices=RecommendationType.choices)
    content = models.TextField()
    # Optional structured payload for Responses API
    content_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # Add this field

    def __str__(self):
        return f"{self.pet.name} - {self.get_type_display()} - {self.created_at.strftime('%Y-%m-%d')}"

class AIHealthReport(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='ai_health_reports')
    summary = models.TextField()
    suggestions = models.TextField(blank=True, null=True)
    # Optional structured payload for Responses API
    summary_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # Add this field

    def __str__(self):
        return f"{self.pet.name} - Health Report - {self.created_at.strftime('%Y-%m-%d')}"

