from django.contrib import admin
from .models import Clinic, VetProfile, ReferralCode, ReferredUser, ReferralStatus


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = (
        "name", "city", "owner", "email_status", "admin_status", 
        "public_status", "latitude", "longitude", "created_at"
    )
    list_filter = (
        "email_confirmed", "admin_approved", "is_verified", 
        "city", "created_at"
    )
    search_fields = (
        "name", "city", "address", "email", 
        "owner__email", "owner__first_name", "owner__last_name"
    )
    readonly_fields = (
        "created_at", "updated_at", "slug", 
        "email_confirmation_token", "email_confirmation_sent_at"
    )
    prepopulated_fields = {}
    ordering = ("name",)

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'city', 'address', 'latitude', 'longitude', 'phone', 'email', 'website')
        }),
        ('Social & Professional', {
            'fields': ('instagram', 'specializations', 'working_hours', 'bio', 'logo')
        }),
        ('Owner & Management', {
            'fields': ('owner',)
        }),
        ('Verification Status', {
            'fields': ('email_confirmed', 'admin_approved', 'is_verified'),
            'description': 'Email confirmation is automatic. Admin approval and verification are manual.'
        }),
        ('Email Confirmation Details', {
            'fields': ('email_confirmation_sent_at', 'email_confirmation_token'),
            'classes': ('collapse',),
            'description': 'Email confirmation tracking (automatic)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    actions = [
        "mark_verified", "mark_unverified", "approve_clinics", 
        "disapprove_clinics", "create_or_refresh_referral_code", "report_nearby_users"
    ]

    def email_status(self, obj):
        if obj.email_confirmed:
            return "✅ Confirmed"
        else:
            return "❌ Pending"
    email_status.short_description = "Email Status"

    def admin_status(self, obj):
        if obj.admin_approved:
            return "✅ Approved"
        else:
            return "⏳ Pending"
    admin_status.short_description = "Admin Approval"

    def public_status(self, obj):
        if obj.email_confirmed and obj.admin_approved:
            return "🌐 Public + Verified"
        elif obj.email_confirmed:
            return "📋 Public (No Badge)"
        else:
            return "🔒 Hidden"
    public_status.short_description = "Public Listing"

    @admin.action(description="Approve selected clinics (admin approval)")
    def approve_clinics(self, request, queryset):
        updated = 0
        for clinic in queryset:
            clinic.admin_approved = True
            clinic.save()
            updated += 1
        self.message_user(request, f"{updated} clinic(s) approved by admin.")

    @admin.action(description="Disapprove selected clinics")
    def disapprove_clinics(self, request, queryset):
        updated = queryset.update(admin_approved=False, is_verified=False)
        self.message_user(request, f"{updated} clinic(s) disapproved.")

    @admin.action(description="Mark selected clinics as Verified (public listing)")
    def mark_verified(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f"{updated} clinic(s) marked as verified.")

    @admin.action(description="Mark selected clinics as Unverified (hidden)")
    def mark_unverified(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f"{updated} clinic(s) marked as unverified.")

    @admin.action(description="Create default referral code (if none) or refresh (add new active)")
    def create_or_refresh_referral_code(self, request, queryset):
        created = 0
        for clinic in queryset:
            # create a new active code (you may want to deactivate old ones)
            ReferralCode.create_default_for_clinic(clinic)
            created += 1
        self.message_user(request, f"Created new referral codes for {created} clinic(s).")

    @admin.action(description="Generate proximity user report for selected clinic (single)")
    def report_nearby_users(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Select exactly one clinic to generate report", level='error')
            return
        clinic = queryset.first()
        from django.urls import reverse
        report_url = reverse('vets:clinic_nearby_users_report', kwargs={'clinic_id': clinic.id})
        self.message_user(request, f"Proximity report: {report_url}")


@admin.register(VetProfile)
class VetProfileAdmin(admin.ModelAdmin):
    list_display = ("vet_name", "clinic", "degrees")
    search_fields = ("vet_name", "clinic__name", "degrees", "certifications")


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "clinic", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("code", "clinic__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ReferredUser)
class ReferredUserAdmin(admin.ModelAdmin):
    list_display = ("__str__", "clinic", "status", "created_at")
    list_filter = ("status", "created_at", "clinic")
    search_fields = ("user__email", "email_capture", "clinic__name", "referral_code__code")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("clinic", "referral_code", "user")

    actions = ["mark_active", "mark_inactive"]

    @admin.action(description="Mark selected referrals as ACTIVE")
    def mark_active(self, request, queryset):
        updated = queryset.update(status=ReferralStatus.ACTIVE)
        self.message_user(request, f"{updated} referral(s) set to ACTIVE.")

    @admin.action(description="Mark selected referrals as INACTIVE")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(status=ReferralStatus.INACTIVE)
        self.message_user(request, f"{updated} referral(s) set to INACTIVE.")
