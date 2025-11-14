from __future__ import annotations
from django.db import models
import secrets
import string

from django.conf import settings
from django.db import models
from django.template.defaultfilters import slugify
from django.urls import reverse

# ---------- helpers ----------
def _rand_suffix(n: int = 5) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))

def _gen_ref_code(prefix: str = "vet") -> str:
    # e.g. vet-a1b2c
    return f"{prefix}-{_rand_suffix(5)}"

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# ---------- core models ----------
class Clinic(TimeStampedModel):
    """
    A veterinarian or clinic with a public page on FAMMO.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_clinics",
        help_text="Account that manages this clinic page.",
    )
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    city = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=220, blank=True)
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="Latitude coordinate for location"
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        help_text="Longitude coordinate for location"
    )
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    instagram = models.CharField(max_length=120, blank=True, help_text="Handle or URL")
    specializations = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated (e.g., Cats, Dogs, Nutrition)",
    )
    working_hours = models.CharField(
        max_length=160, blank=True, help_text="e.g., Mon–Sat 09:00–18:00"
    )
    bio = models.TextField(blank=True)
    logo = models.ImageField(upload_to="clinic_logos/", blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    # Email confirmation and approval fields
    email_confirmed = models.BooleanField(default=False, help_text="Email address has been confirmed")
    admin_approved = models.BooleanField(default=False, help_text="Approved by admin for public listing")
    email_confirmation_token = models.CharField(max_length=100, blank=True)
    email_confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def is_active_clinic(self):
        """Clinic is active only if both email confirmed and admin approved"""
        return self.email_confirmed and self.admin_approved

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # auto-generate a unique slug
        if not self.slug:
            base = slugify(self.name) or "clinic"
            slug_candidate = base
            i = 1
            while Clinic.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
                i += 1
                slug_candidate = f"{base}-{i}"
            self.slug = slug_candidate
        
        # Auto-geocode if coordinates are missing but address exists
        if (not self.latitude or not self.longitude) and (self.address or self.city):
            from .utils import geocode_address
            import logging
            logger = logging.getLogger(__name__)
            
            coords = geocode_address(self.address, self.city)
            if coords:
                self.latitude, self.longitude = coords
                # Use logger instead of print to avoid encoding issues
                logger.info(f"Auto-geocoded {self.name}: {self.latitude}, {self.longitude}")
        
        
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("vets:clinic_detail", kwargs={"slug": self.slug})

    @property
    def active_referral_code(self) -> str | None:
        """Return referral code if clinic has confirmed email (even if not admin approved)"""
        if not self.email_confirmed:
            return None
        code = self.referral_codes.filter(is_active=True).order_by("created_at").first()
        return code.code if code else None


class VetProfile(TimeStampedModel):
    """
    Optional: lead veterinarian details tied to a Clinic.
    Keep if you want a person profile distinct from the clinic brand.
    """
    clinic = models.OneToOneField(Clinic, on_delete=models.CASCADE, related_name="vet_profile")
    vet_name = models.CharField(max_length=120)
    degrees = models.CharField(max_length=200, blank=True, help_text="e.g., DVM, MSc Nutrition")
    certifications = models.CharField(max_length=240, blank=True)

    def __str__(self) -> str:
        return f"{self.vet_name} @ {self.clinic.name}"


class ReferralCode(TimeStampedModel):
    """
    Unique referral code for a clinic. Used in signup URLs: /signup/?ref=<code>
    """
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="referral_codes")
    code = models.SlugField(max_length=40, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["code"])]

    def __str__(self) -> str:
        return f"{self.code} → {self.clinic.name}"

    @staticmethod
    def create_default_for_clinic(clinic: Clinic) -> "ReferralCode":
        """
        Create a readable, unique code based on clinic slug; fall back to random.
        """
        if clinic.slug:
            base = clinic.slug.replace("-", "")[:10]
            candidate = f"vet-{base or _rand_suffix(4)}"
        else:
            candidate = _gen_ref_code()
        # ensure uniqueness
        while ReferralCode.objects.filter(code=candidate).exists():
            candidate = _gen_ref_code()
        return ReferralCode.objects.create(clinic=clinic, code=candidate, is_active=True)


class ReferralStatus(models.TextChoices):
    NEW = "NEW", "New"
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"


class ReferredUser(TimeStampedModel):
    """
    Tracks users who arrive via a clinic's referral link.
    If signup hasn't completed yet, keep email_capture until the account is created.
    """
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name="referred_users")
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinic_referrals",
    )
    email_capture = models.EmailField(blank=True)
    status = models.CharField(max_length=10, choices=ReferralStatus.choices, default=ReferralStatus.NEW)

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["clinic", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        who = getattr(self.user, "email", None) if self.user_id else (self.email_capture or "anonymous")
        return f"{who} via {self.clinic.name} ({self.status})"
