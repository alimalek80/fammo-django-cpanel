from django.db import models
from django.utils.crypto import get_random_string

# Create your models here.

class HeroSection(models.Model):
    """Model to store the content for the homepage hero section."""
    heading = models.CharField(max_length=200, help_text="The main title, e.g., 'Healthy Meals, Happy Pets!'")
    subheading = models.TextField(help_text="The paragraph text below the main title.")
    subheading_secondary = models.CharField(max_length=200, blank=True, help_text="An extra line under the main subheading, e.g., in red.")
    button_text = models.CharField(max_length=50, help_text="The text for the call-to-action button.")
    button_url = models.CharField(max_length=200, help_text="The URL the button links to. Can be a full URL or a Django URL name like '/pets/create/'.")
    background_image = models.ImageField(upload_to='hero_backgrounds/', help_text="Background image. Recommended size: 1920x1080px.")
    is_active = models.BooleanField(default=True, help_text="Only one hero section can be active at a time.")

    def save(self, *args, **kwargs):
        # Ensure only one instance is active
        if self.is_active:
            HeroSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Homepage Hero Section - {self.heading}"

    class Meta:
        verbose_name = "Homepage Hero Section"
        verbose_name_plural = "Homepage Hero Sections"

class Lead(models.Model):
    PET_TYPES = (("cat","Cat"),("dog","Dog"))
    uuid = models.CharField(max_length=22, unique=True)
    pet_type = models.CharField(max_length=10, choices=PET_TYPES)
    weight = models.DecimalField(max_digits=5, decimal_places=1)
    email = models.EmailField()
    source = models.CharField(max_length=50, blank=True, default="instagram")
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = get_random_string(22)
        super().save(*args, **kwargs)

    def __str__(self): 
        return f"{self.email} • {self.pet_type} • {self.weight}kg"

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["-created_at"]

class SocialLinks(models.Model):
    instagram = models.URLField(blank=True, null=True)
    x = models.URLField("X (Twitter)", blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name = "Social Links"
        verbose_name_plural = "Social Links"

    def __str__(self):
        return "Social Media Links"


class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower appears first")
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-updated_at"]

    def __str__(self):
        return self.question

class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    subject = models.CharField(max_length=180, blank=True)
    message = models.TextField()
    consent = models.BooleanField(default=False, help_text="User consented to be contacted")
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject or 'No subject'}"
