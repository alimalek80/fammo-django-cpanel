from django.contrib import admin
from .models import AIRecommendation, AIHealthReport

@admin.register(AIRecommendation)
class AIRecommendationAdmin(admin.ModelAdmin):
    list_display = ('pet', 'get_user', 'type', 'ip_address', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('pet__name', 'content', 'ip_address', 'pet__user__email')

    def get_user(self, obj):
        return obj.pet.user if hasattr(obj.pet, 'user') else None
    get_user.short_description = 'User'

@admin.register(AIHealthReport)
class AIHealthReportAdmin(admin.ModelAdmin):
    list_display = ('pet', 'get_user', 'ip_address', 'created_at')
    search_fields = ('pet__name', 'summary', 'ip_address', 'pet__user__email')

    def get_user(self, obj):
        return obj.pet.user if hasattr(obj.pet, 'user') else None
    get_user.short_description = 'User'
