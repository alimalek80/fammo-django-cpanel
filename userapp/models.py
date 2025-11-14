from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager
from django.utils import timezone
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from subscription.models import SubscriptionPlan

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email
    

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    first_name = models.CharField(_("First Name"), max_length=100)
    last_name = models.CharField(_("Last Name"), max_length=100)
    phone = models.CharField(_("Phone Number"), max_length=20)
    address = models.TextField(_("Address"))
    city = models.CharField(_("City"), max_length=100)
    zip_code = models.CharField(_("ZIP Code"), max_length=20)
    country = models.CharField(_("Country"), max_length=100)
    
    # Optional location fields for proximity features
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_consent = models.BooleanField(default=False, help_text="User consented to store approximate location")
    location_updated_at = models.DateTimeField(null=True, blank=True)

    subscription_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
        related_name='profiles'
    )
    
    is_writer = models.BooleanField(default=False, verbose_name="Writer")

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.user.email}"
