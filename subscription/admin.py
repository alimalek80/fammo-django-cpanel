from django.contrib import admin
from .models import SubscriptionPlan, AIUsage
from markdownx.admin import MarkdownxModelAdmin

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(MarkdownxModelAdmin):
    list_display = ('name', 'monthly_meal_limit', 'monthly_health_limit', 'price_eur', 'unlimited_meals', 'unlimited_health')
    fields = ('name', 'price_eur', 'monthly_meal_limit', 'unlimited_meals', 'monthly_health_limit', 'unlimited_health', 'description')
    list_filter = ('name',)
    search_fields = ('name',)

@admin.register(AIUsage)
class AIUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'month', 'meal_used', 'health_used')
    list_filter = ('month', 'user')
    search_fields = ('user__email',)
