from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Clinic, ReferralCode


@receiver(post_save, sender=Clinic)
def create_referral_code_on_clinic_create(sender, instance: Clinic, created, **kwargs):
    """
    Create referral code when clinic confirms email (even if not admin approved yet)
    """
    if created:
        # Don't create referral code immediately on creation
        # It will be created when clinic confirms email
        pass
    else:
        # Check if clinic has confirmed email (regardless of admin approval)
        if instance.email_confirmed:
            # If no active code exists, create one
            has_active = instance.referral_codes.filter(is_active=True).exists()
            if not has_active:
                ReferralCode.create_default_for_clinic(instance)


@receiver(post_save, sender=Clinic)
def update_clinic_verification_status(sender, instance, **kwargs):
    """
    Automatically update is_verified when both email_confirmed and admin_approved are True
    """
    # Check if both conditions are met but is_verified is False
    if instance.email_confirmed and instance.admin_approved and not instance.is_verified:
        # Prevent recursive calls by using update instead of save
        Clinic.objects.filter(pk=instance.pk).update(is_verified=True)
    
    # Check if either condition is not met but is_verified is True
    elif (not instance.email_confirmed or not instance.admin_approved) and instance.is_verified:
        # Remove verification if either condition is no longer met
        Clinic.objects.filter(pk=instance.pk).update(is_verified=False)


@receiver(post_save, sender=Clinic)
def update_clinic_verification_status(sender, instance: Clinic, **kwargs):
    """
    Automatically update is_verified when both email_confirmed and admin_approved are True
    """
    should_be_verified = instance.email_confirmed and instance.admin_approved
    
    if should_be_verified and not instance.is_verified:
        # Update without triggering another post_save
        Clinic.objects.filter(pk=instance.pk).update(is_verified=True)
    elif not should_be_verified and instance.is_verified:
        # Remove verification if either condition is no longer met
        Clinic.objects.filter(pk=instance.pk).update(is_verified=False)
