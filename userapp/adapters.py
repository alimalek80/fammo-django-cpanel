from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return True
    
    def get_signup_redirect_url(self, request):
        # Capture referral code from URL parameter and store in session
        ref_code = request.GET.get('ref')
        if ref_code:
            request.session['referral_code'] = ref_code
            # Track the referral visit
            try:
                from vets.models import ReferralCode, ReferredUser, ReferralStatus
                ref_code_obj = ReferralCode.objects.get(code=ref_code, is_active=True)
                
                # Create a tracking record for the visit (before registration)
                ReferredUser.objects.get_or_create(
                    clinic=ref_code_obj.clinic,
                    email_capture='',  # Will be filled when user registers
                    referral_code=ref_code_obj,
                    defaults={'status': ReferralStatus.NEW}
                )
                print(f"Referral tracking: Captured visit for clinic {ref_code_obj.clinic.name}")
                
            except Exception as e:
                print(f"Error tracking referral visit: {e}")
        
        return super().get_signup_redirect_url(request)

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        user.is_active = True
        print("CustomAccountAdapter: Activated user on save_user")
        
        # Handle referral tracking after user registration
        referral_code = request.session.get('referral_code')
        if referral_code:
            try:
                from vets.models import ReferralCode, ReferredUser, ReferralStatus
                ref_code_obj = ReferralCode.objects.get(code=referral_code, is_active=True)
                
                # Create or update referral tracking
                referred_user, created = ReferredUser.objects.get_or_create(
                    clinic=ref_code_obj.clinic,
                    user=user,
                    defaults={
                        'referral_code': ref_code_obj,
                        'email_capture': user.email,
                        'status': ReferralStatus.NEW
                    }
                )
                
                if not created:
                    # Update existing record
                    referred_user.user = user
                    referred_user.email_capture = user.email
                    referred_user.status = ReferralStatus.NEW
                    referred_user.save()
                
                print(f"Referral tracking: Linked user {user.email} to clinic {ref_code_obj.clinic.name}")
                
                # Clear the referral code from session
                del request.session['referral_code']
                
            except Exception as e:
                print(f"Error processing referral on user save: {e}")
        
        if commit:
            user.save()
        return user

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_auto_signup_allowed(self, request, sociallogin):
        # Always allow auto signup for social accounts
        return True

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.is_active = True
        user.save()
        
        # Handle referral tracking for social signup
        referral_code = request.session.get('referral_code')
        if referral_code:
            try:
                from vets.models import ReferralCode, ReferredUser, ReferralStatus
                ref_code_obj = ReferralCode.objects.get(code=referral_code, is_active=True)
                
                # Create referral tracking for social signup
                referred_user, created = ReferredUser.objects.get_or_create(
                    clinic=ref_code_obj.clinic,
                    user=user,
                    defaults={
                        'referral_code': ref_code_obj,
                        'email_capture': user.email,
                        'status': ReferralStatus.NEW
                    }
                )
                
                print(f"Social referral tracking: Linked user {user.email} to clinic {ref_code_obj.clinic.name}")
                
                # Clear the referral code from session
                del request.session['referral_code']
                
            except Exception as e:
                print(f"Error processing social referral: {e}")
        
        return user