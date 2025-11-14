from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserRegistrationForm, ProfileForm, CustomLoginForm, SetPasswordForm
from .models import Profile
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from collections import Counter
from pet.models import Pet
from aihub.models import AIRecommendation, AIHealthReport
from aihub.utils import get_country_from_ip
import csv
from django.http import HttpResponse, JsonResponse
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from datetime import timedelta
from django.utils import timezone
import json
from django.conf import settings
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
try:
    from allauth.socialaccount.models import SocialApp
except ImportError:
    SocialApp = None  # Fallback if allauth not available for some reason


def _google_enabled():
    """Return True if a Google SocialApp is configured for the active SITE_ID.
    Safe to call when SocialApp model isn't present.
    """
    if not SocialApp:
        return False
    try:
        return SocialApp.objects.filter(provider='google', sites__id=settings.SITE_ID).exists()
    except Exception:
        return False


def terms_and_conditions_view(request):
    return render(request, 'userapp/terms_and_conditions.html')


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User inactive until email confirmation
            user.save()
            
            # Handle referral tracking
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
                        referred_user.status = ReferralStatus.NEW
                        referred_user.save()
                    
                    # Store referral info for activation
                    request.session['pending_referral'] = {
                        'clinic_id': ref_code_obj.clinic.id,
                        'referral_code': referral_code
                    }
                    
                except Exception as e:
                    # Log error but don't break registration
                    print(f"Error tracking referral during registration: {e}")
            
            # Send activation email
            current_site = get_current_site(request)
            subject = "Activate your FAMO account"
            message = render_to_string('userapp/account_activation_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            send_mail(subject, message, None, [user.email])
            messages.success(request, _("Registration successful. Please check your email to activate your account."))
            return redirect('login')
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = UserRegistrationForm()
        
        # Capture referral code from URL parameter and store in session
        ref_code = request.GET.get('ref')
        if ref_code:
            request.session['referral_code'] = ref_code
            # Also track the referral visit
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
                
                # Add clinic info to context for the registration form
                request.referring_clinic = ref_code_obj.clinic
                
            except Exception as e:
                print(f"Error tracking referral visit: {e}")
    
    # Get referring clinic info if available
    referring_clinic = getattr(request, 'referring_clinic', None)
    if not referring_clinic and request.session.get('referral_code'):
        try:
            from vets.models import ReferralCode
            ref_code_obj = ReferralCode.objects.get(
                code=request.session['referral_code'], 
                is_active=True
            )
            referring_clinic = ref_code_obj.clinic
        except:
            pass
    
    return render(request, 'userapp/register.html', {
        'form': form,
        'referring_clinic': referring_clinic,
        'referral_code': request.session.get('referral_code'),
        'google_enabled': _google_enabled(),
    })

def login_view(request):
    if request.user.is_authenticated:
        messages.info(request, _("You are already logged in."))
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, _("Login successful."))
            return redirect('dashboard')
        else:
            messages.error(request, _("Invalid login credentials."))
        form = CustomLoginForm(request, data=request.POST)
    else:
        form = CustomLoginForm()
    return render(request, 'userapp/login.html', {
        'form': form,
        'google_enabled': _google_enabled(),
    })

def logout_view(request):
    logout(request)
    messages.info(request, _("You have been logged out."))
    return redirect('login')

@login_required
def update_profile(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profile updated successfully."))
            return redirect('dashboard')
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'userapp/update_profile.html', {'form': form})

@login_required
def dashboard_view(request):
    user = request.user
    pets = getattr(user, 'pets', None)
    if pets is not None:
        pets = user.pets.all()
    else:
        pets = []
    has_pets = pets.exists() if hasattr(pets, 'exists') else False
    messages.info(request, _("Welcome to your dashboard!"))
    return render(request, 'userapp/dashboard.html', {
        'has_pets': has_pets,
    })

@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def users_admin_view(request):
    User = get_user_model()
    users = User.objects.all().prefetch_related('pets')
    
    return render(request, 'userapp/users_admin.html', {
        'users': users,
        
    })

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        
        # Handle referral activation
        pending_referral = request.session.get('pending_referral')
        if pending_referral:
            try:
                from vets.models import ReferredUser, ReferralStatus
                
                # Update referral status to ACTIVE when user activates account
                referred_user = ReferredUser.objects.filter(
                    clinic_id=pending_referral['clinic_id'],
                    user=user
                ).first()
                
                if referred_user:
                    referred_user.status = ReferralStatus.ACTIVE
                    referred_user.save()
                    print(f"✅ Referral activated for user {user.email} from clinic {referred_user.clinic.name}")
                
                # Clear the session
                del request.session['pending_referral']
                
            except Exception as e:
                print(f"Error activating referral: {e}")
        
        # Check if there's pending pet data from wizard registration
        pending_pet_key = f'pending_pet_data_{user.pk}'
        pet_created = False
        pet_name = None
        
        if pending_pet_key in request.session:
            try:
                from pet.models import Pet, PetType, Gender, AgeCategory, Breed, FoodFeeling, FoodImportance, BodyType, ActivityLevel, TreatFrequency, FoodType, FoodAllergy, HealthIssue
                
                pet_data = request.session[pending_pet_key]
                pet_name = pet_data.get('name')
                
                # Check if pet was already created during registration (it should be)
                existing_pet = Pet.objects.filter(user=user, name=pet_name).first()
                if existing_pet:
                    pet_created = True
                    print(f"✅ Pet '{pet_name}' already exists for user {user.email}")  # Debug log
                else:
                    # Fallback: create pet if it doesn't exist for some reason
                    pet = Pet(user=user)
                    pet.name = pet_data.get('name')
                    
                    # Handle foreign key relationships
                    if pet_data.get('pet_type_id'):
                        pet.pet_type = PetType.objects.get(pk=pet_data['pet_type_id'])
                    if pet_data.get('gender_id'):
                        pet.gender = Gender.objects.get(pk=pet_data['gender_id'])
                    if pet_data.get('age_category_id'):
                        pet.age_category = AgeCategory.objects.get(pk=pet_data['age_category_id'])
                    if pet_data.get('breed_id'):
                        pet.breed = Breed.objects.get(pk=pet_data['breed_id'])
                    if pet_data.get('food_feeling_id'):
                        pet.food_feeling = FoodFeeling.objects.get(pk=pet_data['food_feeling_id'])
                    if pet_data.get('food_importance_id'):
                        pet.food_importance = FoodImportance.objects.get(pk=pet_data['food_importance_id'])
                    if pet_data.get('body_type_id'):
                        pet.body_type = BodyType.objects.get(pk=pet_data['body_type_id'])
                    if pet_data.get('activity_level_id'):
                        pet.activity_level = ActivityLevel.objects.get(pk=pet_data['activity_level_id'])
                    if pet_data.get('treat_frequency_id'):
                        pet.treat_frequency = TreatFrequency.objects.get(pk=pet_data['treat_frequency_id'])
                    
                    # Handle simple fields
                    pet.neutered = pet_data.get('neutered')
                    pet.age_years = pet_data.get('age_years')
                    pet.age_months = pet_data.get('age_months')
                    pet.age_weeks = pet_data.get('age_weeks')
                    pet.unknown_breed = pet_data.get('unknown_breed')
                    pet.food_allergy_other = pet_data.get('food_allergy_other')
                    
                    # Handle weight conversion
                    if pet_data.get('weight'):
                        from decimal import Decimal
                        pet.weight = Decimal(pet_data['weight'])
                    
                    pet.save()
                    
                    # Handle many-to-many relationships
                    if pet_data.get('food_types_ids'):
                        food_types = FoodType.objects.filter(pk__in=pet_data['food_types_ids'])
                        pet.food_types.set(food_types)
                    
                    if pet_data.get('food_allergies_ids'):
                        food_allergies = FoodAllergy.objects.filter(pk__in=pet_data['food_allergies_ids'])
                        pet.food_allergies.set(food_allergies)
                    
                    if pet_data.get('health_issues_ids'):
                        health_issues = HealthIssue.objects.filter(pk__in=pet_data['health_issues_ids'])
                        pet.health_issues.set(health_issues)
                    
                    pet_created = True
                    print(f"✅ Pet '{pet_name}' created during activation for user {user.email}")  # Debug log
                
                # Clear the session data
                del request.session[pending_pet_key]
                
            except Exception as e:
                print(f"❌ Error during pet creation at activation: {e}")  # Debug log
                # If pet creation fails, still proceed with activation
                if pending_pet_key in request.session:
                    del request.session[pending_pet_key]
        
        # Store activation info in session for password setup
        request.session['newly_activated_user_id'] = user.pk
        if pet_created and pet_name:
            request.session['activated_with_pet'] = pet_name
        
        # Redirect to password setup instead of login
        return redirect('set_password_after_activation')
    else:
        messages.error(request, _("Activation link is invalid!"))
        return redirect('login')


def set_password_after_activation(request):
    """Set password after email activation"""
    # Check if user just activated their account
    if 'newly_activated_user_id' not in request.session:
        messages.error(request, _("Invalid access. Please use the activation link from your email."))
        return redirect('login')
    
    user_id = request.session['newly_activated_user_id']
    pet_name = request.session.get('activated_with_pet')
    
    try:
        User = get_user_model()
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        messages.error(request, _("User not found or not activated."))
        return redirect('login')
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            # Set the new password
            user.set_password(form.cleaned_data['password1'])
            user.save()
            
            # Clear session data
            del request.session['newly_activated_user_id']
            if 'activated_with_pet' in request.session:
                del request.session['activated_with_pet']
            
            # Log the user in automatically
            from django.contrib.auth import login
            login(request, user)
            
            # Show success message
            if pet_name:
                messages.success(request, _(f"🎉 Welcome to FAMO-PET! Your password has been set and {pet_name}'s profile is ready!"))
                return redirect('pet:my_pets')
            else:
                messages.success(request, _("🎉 Welcome to FAMO-PET! Your password has been set successfully!"))
                return redirect('dashboard')
        else:
            messages.error(request, _("Please correct the errors below."))
    else:
        form = SetPasswordForm()
    
    context = {
        'form': form,
        'user_email': user.email,
        'pet_name': pet_name,
    }
    return render(request, 'userapp/set_password.html', context)

@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def admin_dashboard_view(request):
    User = get_user_model()
    total_users = User.objects.count()
    total_pets = Pet.objects.count()
    total_dogs = Pet.objects.filter(pet_type__name__iexact="Dog").count()
    total_cats = Pet.objects.filter(pet_type__name__iexact="Cat").count()
    total_ai_meals = AIRecommendation.objects.count()
    total_ai_health = AIHealthReport.objects.count()

    context = {
        'total_users': total_users,
        'total_pets': total_pets,
        'total_dogs': total_dogs,
        'total_cats': total_cats,
        'total_ai_meals': total_ai_meals,
        'total_ai_health': total_ai_health,
    }
    return render(request, 'userapp/admin_dashboard.html', context)
    
@method_decorator(csrf_protect, name='dispatch')
class SaveUserLocationAPIView(View):
    """Authenticated endpoint to store user approximate location.
    Expects JSON: {"latitude": <float>, "longitude": <float>, "consent": true}
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        lat = data.get('latitude')
        lng = data.get('longitude')
        consent = bool(data.get('consent'))

        if consent and (lat is None or lng is None):
            return JsonResponse({'error': 'Latitude and longitude are required when consent is true'}, status=400)

        profile = getattr(request.user, 'profile', None)
        if profile is None:
            return JsonResponse({'error': 'Profile not found'}, status=404)

        if consent:
            # Validate numeric ranges
            try:
                lat_f = float(lat)
                lng_f = float(lng)
            except (TypeError, ValueError):
                return JsonResponse({'error': 'Invalid coordinate values'}, status=400)
            if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
                return JsonResponse({'error': 'Coordinates out of bounds'}, status=400)
            profile.latitude = lat_f
            profile.longitude = lng_f
            profile.location_consent = True
            profile.location_updated_at = timezone.now()
        else:
            # User revoked consent
            profile.location_consent = False
            profile.latitude = None
            profile.longitude = None
            profile.location_updated_at = timezone.now()
        profile.save(update_fields=["latitude", "longitude", "location_consent", "location_updated_at"])

        return JsonResponse({
            'success': True,
            'consent': profile.location_consent,
            'latitude': float(profile.latitude) if profile.latitude is not None else None,
            'longitude': float(profile.longitude) if profile.longitude is not None else None,
            'updated_at': profile.location_updated_at.isoformat() if profile.location_updated_at else None
        })

@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def admin_dashboard_chart_data(request):
    """API endpoint for fetching filtered chart data"""
    User = get_user_model()
    chart_type = request.GET.get('chart', 'ai_requests')
    period = request.GET.get('period', '30')  # Default to 30 days
    
    # Calculate date range based on period
    now = timezone.now()
    if period == '7':
        start_date = now - timedelta(days=7)
        days_count = 7
        group_by = 'day'
    elif period == '30':
        start_date = now - timedelta(days=30)
        days_count = 30
        group_by = 'day'
    elif period == '90':
        start_date = now - timedelta(days=90)
        days_count = 90
        group_by = 'day'
    elif period == '180':
        start_date = now - timedelta(days=180)
        days_count = 180
        group_by = 'day'
    elif period == '360':
        start_date = now - timedelta(days=360)
        days_count = 360
        group_by = 'day'
    elif period == 'month':
        # Current month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_count = (now - start_date).days + 1
        group_by = 'day'
    elif period == '3months':
        start_date = now - timedelta(days=90)
        days_count = 90
        group_by = 'week'
    elif period == '6months':
        start_date = now - timedelta(days=180)
        days_count = 180
        group_by = 'week'
    else:
        start_date = now - timedelta(days=30)
        days_count = 30
        group_by = 'day'
    
    if chart_type == 'ai_requests':
        # Users with AI requests by date (distinct users per day/week)
        if group_by == 'day':
            meal_pairs = AIRecommendation.objects.filter(
                created_at__gte=start_date
            ).annotate(date=TruncDate('created_at')).values_list('date', 'pet__user_id')
            health_pairs = AIHealthReport.objects.filter(
                created_at__gte=start_date
            ).annotate(date=TruncDate('created_at')).values_list('date', 'pet__user_id')

            # Build map of date -> set(user_ids)
            date_users = {}
            for d, uid in list(meal_pairs) + list(health_pairs):
                if d is None or uid is None:
                    continue
                key = str(d)
                if key not in date_users:
                    date_users[key] = set()
                date_users[key].add(uid)

            labels = []
            data = []
            for i in range(days_count):
                day = (start_date + timedelta(days=i)).date()
                key = day.strftime('%Y-%m-%d')
                labels.append(key)
                data.append(len(date_users.get(key, set())))

        elif group_by == 'week':
            # Aggregate by week (start on Monday)
            meal_events = AIRecommendation.objects.filter(
                created_at__gte=start_date
            ).values_list('created_at', 'pet__user_id')
            health_events = AIHealthReport.objects.filter(
                created_at__gte=start_date
            ).values_list('created_at', 'pet__user_id')

            week_users = {}
            for dt, uid in list(meal_events) + list(health_events):
                if dt is None or uid is None:
                    continue
                d = dt.date()
                week_start = d - timedelta(days=d.weekday())
                key = week_start.strftime('%Y-%m-%d')
                if key not in week_users:
                    week_users[key] = set()
                week_users[key].add(uid)

            # Build continuous weekly labels from start to now
            start_week = (start_date.date() - timedelta(days=start_date.weekday()))
            end_week = (now.date() - timedelta(days=now.weekday()))
            labels = []
            data = []
            cur = start_week
            while cur <= end_week:
                key = cur.strftime('%Y-%m-%d')
                labels.append(key)
                data.append(len(week_users.get(key, set())))
                cur = cur + timedelta(days=7)

        return JsonResponse({
            'labels': labels,
            'data': data
        })
    
    elif chart_type == 'user_registrations':
        # User Registrations by Date
        if group_by == 'day':
            registrations = (
                User.objects.filter(date_joined__gte=start_date)
                .annotate(date=TruncDate('date_joined'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            )
            
            reg_dict = {str(item['date']): item['count'] for item in registrations}
            labels = []
            data = []
            
            for i in range(days_count):
                date = (start_date + timedelta(days=i)).date()
                labels.append(date.strftime('%Y-%m-%d'))
                data.append(reg_dict.get(str(date), 0))
        
        elif group_by == 'week':
            # Group by weeks
            registrations = list(User.objects.filter(date_joined__gte=start_date))
            weeks_dict = {}
            
            for user in registrations:
                # Calculate week number
                week_start = user.date_joined.date() - timedelta(days=user.date_joined.weekday())
                week_label = week_start.strftime('%Y-%m-%d')
                weeks_dict[week_label] = weeks_dict.get(week_label, 0) + 1
            
            # Sort by date
            sorted_weeks = sorted(weeks_dict.items())
            labels = [week for week, _ in sorted_weeks]
            data = [count for _, count in sorted_weeks]
        
        return JsonResponse({
            'labels': labels,
            'data': data
        })
    
    elif chart_type == 'user_countries':
        # User Registrations by Country
        users_by_country = (
            Profile.objects.filter(user__date_joined__gte=start_date)
            .exclude(country='')
            .values('country')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        return JsonResponse({
            'labels': [item['country'] for item in users_by_country],
            'data': [item['count'] for item in users_by_country]
        })
    
    return JsonResponse({'error': 'Invalid chart type'}, status=400)

@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def admin_dashboard_kpis(request):
    """Return summary KPIs and growth rates for the dashboard report.

    Query params:
      users_period: period for user growth window (7|30|90|180|360|month)
      ai_period:    period for AI requests growth window (same options)
    """
    User = get_user_model()

    def parse_period(p):
        now = timezone.now()
        if p == '7':
            return now - timedelta(days=7), now, 7
        if p == '30':
            return now - timedelta(days=30), now, 30
        if p == '90':
            return now - timedelta(days=90), now, 90
        if p == '180':
            return now - timedelta(days=180), now, 180
        if p == '360':
            return now - timedelta(days=360), now, 360
        if p == 'month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return start, now, (now - start).days + 1
        # default
        return now - timedelta(days=30), now, 30

    def growth(current, previous):
        if previous and previous != 0:
            return round(((current - previous) / previous) * 100.0, 2)
        return 100.0 if current > 0 else 0.0

    users_period = request.GET.get('users_period', '30')
    ai_period = request.GET.get('ai_period', '30')

    u_start, u_end, u_days = parse_period(users_period)
    u_prev_start = u_start - timedelta(days=u_days)
    u_prev_end = u_start

    a_start, a_end, a_days = parse_period(ai_period)
    a_prev_start = a_start - timedelta(days=a_days)
    a_prev_end = a_start

    total_users = User.objects.count()
    total_pets = Pet.objects.count()
    total_dogs = Pet.objects.filter(pet_type__name__iexact="Dog").count()
    total_cats = Pet.objects.filter(pet_type__name__iexact="Cat").count()
    total_ai_meals = AIRecommendation.objects.count()
    total_ai_health = AIHealthReport.objects.count()
    total_ai_requests = total_ai_meals + total_ai_health

    current_user_regs = User.objects.filter(date_joined__gte=u_start, date_joined__lt=u_end).count()
    prev_user_regs = User.objects.filter(date_joined__gte=u_prev_start, date_joined__lt=u_prev_end).count()

    current_ai_reqs = (
        AIRecommendation.objects.filter(created_at__gte=a_start, created_at__lt=a_end).count()
        + AIHealthReport.objects.filter(created_at__gte=a_start, created_at__lt=a_end).count()
    )
    prev_ai_reqs = (
        AIRecommendation.objects.filter(created_at__gte=a_prev_start, created_at__lt=a_prev_end).count()
        + AIHealthReport.objects.filter(created_at__gte=a_prev_start, created_at__lt=a_prev_end).count()
    )

    return JsonResponse({
        'totals': {
            'users': total_users,
            'pets': total_pets,
            'dogs': total_dogs,
            'cats': total_cats,
            'ai_requests': total_ai_requests,
            'ai_meals': total_ai_meals,
            'ai_health': total_ai_health,
        },
        'growth': {
            'users': {
                'current': current_user_regs,
                'previous': prev_user_regs,
                'percent': growth(current_user_regs, prev_user_regs),
                'period': users_period,
            },
            'ai_requests': {
                'current': current_ai_reqs,
                'previous': prev_ai_reqs,
                'percent': growth(current_ai_reqs, prev_ai_reqs),
                'period': ai_period,
            }
        }
    })

@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def export_users_csv(request):
    User = get_user_model()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    # Write header
    writer.writerow(['ID', 'Email', 'Full Name', 'Date Joined', 'Is Staff', 'Is Superuser'])
    # Write data
    for user in User.objects.all():
        # Get full name from profile if exists
        if hasattr(user, 'profile'):
            full_name = f"{user.profile.first_name} {user.profile.last_name}".strip()
        else:
            full_name = ""
        writer.writerow([
            user.id,
            user.email,
            full_name,
            user.date_joined,
            user.is_staff,
            user.is_superuser
        ])
    return response
