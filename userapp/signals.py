from django.conf import settings
from django.core.mail import send_mail
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from .models import CustomUser, Profile
from subscription.models import SubscriptionPlan

User = get_user_model()

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        default_plan = SubscriptionPlan.objects.filter(name='free').first()
        Profile.objects.create(user=instance, subscription_plan=default_plan)
        
        
@receiver(post_save, sender=User)
def notify_admin_on_signup(sender, instance, created, **kwargs):
    if created:
        send_mail(
            subject="New User Signup",
            message=f"A new user has signed up: {instance.email}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],  # or your admin email
            fail_silently=True,
        )
