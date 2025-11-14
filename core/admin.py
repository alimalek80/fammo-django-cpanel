from django.contrib import admin
from .models import HeroSection, SocialLinks, FAQ, ContactMessage, Lead
from modeltranslation.admin import TranslationAdmin

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('email', 'pet_type', 'weight', 'source', 'created_at', 'processed')
    list_filter = ('pet_type', 'source', 'processed', 'created_at')
    search_fields = ('email', 'uuid')
    readonly_fields = ('uuid', 'created_at')

@admin.register(HeroSection)
class HeroSectionAdmin(TranslationAdmin):
    list_display = ("heading", "is_active")
    list_editable = ("is_active",)
    search_fields = ("heading", "subheading")

@admin.register(SocialLinks)
class SocialLinksAdmin(admin.ModelAdmin):
    list_display = ("instagram", "x", "facebook", "linkedin")

@admin.register(FAQ)
class FAQAdmin(TranslationAdmin):
    list_display = ("question", "is_published", "sort_order", "updated_at")
    list_editable = ("is_published", "sort_order")
    search_fields = ("question", "answer")
    ordering = ("sort_order", "-updated_at")
    
@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "is_resolved", "created_at")
    list_filter = ("is_resolved", "created_at")
    search_fields = ("name", "email", "subject", "message")
