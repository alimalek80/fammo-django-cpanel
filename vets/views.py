from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import (
    CreateView, DetailView, ListView, UpdateView, 
    TemplateView, View
)
from django.db.models import Q, Count
from django.http import JsonResponse, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import json

from .models import Clinic, VetProfile, ReferralCode, ReferredUser, ReferralStatus
from .forms import (
    ClinicRegistrationForm, ClinicProfileForm, VetProfileForm, 
    ReferralCodeForm, ClinicSearchForm
)
from .utils import (
    send_clinic_confirmation_email, send_admin_notification_email,
    confirm_clinic_email, is_confirmation_token_valid
)
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from userapp.models import Profile

User = get_user_model()


class ClinicRegistrationView(CreateView):
    """Clinic registration view with email confirmation"""
    model = Clinic
    form_class = ClinicRegistrationForm
    template_name = 'vets/clinic_register.html'
    success_url = reverse_lazy('vets:clinic_register_success')
    
    def form_valid(self, form):
        # Create user account first
        user = User.objects.create_user(
            email=form.cleaned_data['owner_email'],
            password=form.cleaned_data['owner_password']
        )
        user.is_active = True
        user.save()
        
        # Create clinic and assign owner
        clinic = form.save(commit=False)
        clinic.owner = user
        # Set initial status - email not confirmed, admin not approved
        clinic.email_confirmed = False
        clinic.admin_approved = False
        clinic.is_verified = False  # Keep this False until both confirmations
        clinic.save()
        
        # Create vet profile if provided
        vet_name = form.cleaned_data.get('vet_name')
        if vet_name:
            VetProfile.objects.create(
                clinic=clinic,
                vet_name=vet_name,
                degrees=form.cleaned_data.get('degrees', ''),
                certifications=form.cleaned_data.get('certifications', '')
            )
        
        # Send confirmation email
        email_sent = send_clinic_confirmation_email(self.request, clinic)
        if email_sent:
            messages.success(
                self.request, 
                f'Registration successful! Please check your email to confirm your clinic registration.'
            )
        else:
            messages.warning(
                self.request,
                f'Registration successful, but there was an issue sending the confirmation email. Please contact support.'
            )
        
        # Log the user in with the correct backend
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        return super().form_valid(form)


class ClinicRegistrationSuccessView(TemplateView):
    """Success page after clinic registration"""
    template_name = 'vets/clinic_register_success.html'


class ClinicEmailConfirmationView(View):
    """Handle email confirmation for clinic registration"""
    
    def get(self, request, clinic_id, token):
        try:
            clinic = get_object_or_404(Clinic, id=clinic_id)
            
            # Check if email is already confirmed
            if clinic.email_confirmed:
                messages.info(request, 'Your email has already been confirmed.')
                return render(request, 'vets/email_confirmed.html', {'clinic': clinic})
            
            # Validate token and confirm email
            if confirm_clinic_email(clinic, token):
                # Send admin notification after successful email confirmation
                send_admin_notification_email(request, clinic)
                
                messages.success(
                    request, 
                    'Email confirmed successfully! Your clinic is now pending admin approval.'
                )
                return render(request, 'vets/email_confirmed.html', {'clinic': clinic})
            else:
                messages.error(
                    request,
                    'Invalid or expired confirmation link. Please contact support for assistance.'
                )
                return redirect('vets:partner_clinics')
                
        except Clinic.DoesNotExist:
            messages.error(request, 'Invalid confirmation link.')
            return redirect('vets:partner_clinics')


class PartnerClinicsListView(ListView):
    """Public list of partner clinics - only show fully approved clinics"""
    model = Clinic
    template_name = 'vets/partner_clinics.html'
    context_object_name = 'clinics'
    paginate_by = 12
    
    def get_queryset(self):
        # Show clinics that have confirmed email (public listing)
        # Badge will only show for admin_approved clinics
        queryset = Clinic.objects.filter(
            email_confirmed=True
        ).order_by('name')
        
        # Handle search within email-confirmed clinics
        form = ClinicSearchForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            city = form.cleaned_data.get('city')
            
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(city__icontains=search) |
                    Q(specializations__icontains=search)
                )
            
            if city:
                queryset = queryset.filter(city__icontains=city)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ClinicSearchForm(self.request.GET)
        context['total_clinics'] = self.get_queryset().count()
        return context


class ClinicDetailView(DetailView):
    """Public clinic profile page - show email-confirmed clinics"""
    model = Clinic
    template_name = 'vets/clinic_detail.html'
    context_object_name = 'clinic'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        """Show clinics that have confirmed email"""
        return Clinic.objects.filter(
            email_confirmed=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinic = self.object
        
        # Show referral functionality for email-confirmed clinics (even if not admin approved)
        if clinic.email_confirmed:
            # Get referral code for sharing
            context['referral_code'] = clinic.active_referral_code
            
            # Build referral URL
            if context['referral_code']:
                context['referral_url'] = self.request.build_absolute_uri(
                    reverse('vets:referral_landing', kwargs={'code': context['referral_code']})
                )
        
        return context


class ClinicOwnerRequiredMixin(LoginRequiredMixin):
    """Mixin to ensure user owns a clinic"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        try:
            self.clinic = request.user.owned_clinics.first()
            if not self.clinic:
                messages.error(request, "You don't have a registered clinic.")
                return redirect('vets:clinic_register')
        except:
            messages.error(request, "You don't have a registered clinic.")
            return redirect('vets:clinic_register')
        
        return super().dispatch(request, *args, **kwargs)


class ClinicDashboardView(ClinicOwnerRequiredMixin, TemplateView):
    """Clinic owner dashboard"""
    template_name = 'vets/dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinic = self.clinic
        
        # Basic stats
        context['clinic'] = clinic
        context['total_referrals'] = clinic.referred_users.count()
        context['active_referrals'] = clinic.referred_users.filter(
            status=ReferralStatus.ACTIVE
        ).count()
        context['new_referrals'] = clinic.referred_users.filter(
            status=ReferralStatus.NEW
        ).count()
        
        # Verification status
        context['verification_status'] = {
            'email_confirmed': clinic.email_confirmed,
            'admin_approved': clinic.admin_approved,
            'is_verified': clinic.is_verified,
            'is_public': clinic.is_active_clinic,
        }
        
        # Recent referrals
        context['recent_referrals'] = clinic.referred_users.select_related(
            'user', 'referral_code'
        ).order_by('-created_at')[:10]
        
        # Referral codes (only show if fully approved)
        if clinic.is_active_clinic:
            context['referral_codes'] = clinic.referral_codes.filter(
                is_active=True
            ).order_by('-created_at')
        else:
            context['referral_codes'] = []
        
        return context


class ClinicProfileUpdateView(ClinicOwnerRequiredMixin, UpdateView):
    """Update clinic profile"""
    model = Clinic
    form_class = ClinicProfileForm
    template_name = 'vets/dashboard/profile_update.html'
    success_url = reverse_lazy('vets:clinic_dashboard')
    
    def get_object(self):
        return self.clinic
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add vet profile form
        try:
            vet_profile = self.clinic.vet_profile
            context['vet_form'] = VetProfileForm(
                instance=vet_profile,
                prefix='vet'
            )
        except VetProfile.DoesNotExist:
            context['vet_form'] = VetProfileForm(prefix='vet')
        
        return context
    
    def form_valid(self, form):
        # Handle vet profile form
        vet_form = VetProfileForm(
            self.request.POST,
            prefix='vet'
        )
        
        if vet_form.is_valid():
            vet_data = vet_form.cleaned_data
            if any(vet_data.values()):  # If any vet data is provided
                try:
                    vet_profile = self.clinic.vet_profile
                    for field, value in vet_data.items():
                        setattr(vet_profile, field, value)
                    vet_profile.save()
                except VetProfile.DoesNotExist:
                    VetProfile.objects.create(
                        clinic=self.clinic,
                        **vet_data
                    )
        
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)


class ClinicReferralsView(ClinicOwnerRequiredMixin, TemplateView):
    """Clinic referrals management"""
    template_name = 'vets/dashboard/referrals.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinic = self.clinic
        
        # Referral statistics
        context['clinic'] = clinic
        context['total_referrals'] = clinic.referred_users.count()
        context['new_referrals'] = clinic.referred_users.filter(
            status=ReferralStatus.NEW
        ).count()
        context['active_referrals'] = clinic.referred_users.filter(
            status=ReferralStatus.ACTIVE
        ).count()
        
        # Referrals list with pagination
        referrals = clinic.referred_users.select_related(
            'user', 'referral_code'
        ).order_by('-created_at')
        
        paginator = Paginator(referrals, 20)
        page_number = self.request.GET.get('page')
        context['referrals'] = paginator.get_page(page_number)
        
        # Referral codes
        context['referral_codes'] = clinic.referral_codes.order_by('-created_at')
        context['referral_form'] = ReferralCodeForm(clinic=clinic)
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle new referral code creation"""
        form = ReferralCodeForm(self.clinic, request.POST)
        
        if form.is_valid():
            code = form.cleaned_data.get('code')
            if not code:
                # Generate automatic code
                referral_code = ReferralCode.create_default_for_clinic(self.clinic)
            else:
                # Use custom code
                referral_code = ReferralCode.objects.create(
                    clinic=self.clinic,
                    code=code,
                    is_active=True
                )
            
            messages.success(
                request, 
                f'New referral code "{referral_code.code}" created successfully!'
            )
        else:
            messages.error(request, 'Please correct the errors below.')
        
        return redirect('vets:clinic_referrals')


class ClinicAnalyticsView(ClinicOwnerRequiredMixin, TemplateView):
    """Clinic analytics and statistics"""
    template_name = 'vets/dashboard/analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinic = self.clinic
        
        # Time-based analytics
        now = datetime.now()
        last_30_days = now - timedelta(days=30)
        last_7_days = now - timedelta(days=7)
        
        context['clinic'] = clinic
        
        # Referral statistics
        context['stats'] = {
            'total_referrals': clinic.referred_users.count(),
            'referrals_30_days': clinic.referred_users.filter(
                created_at__gte=last_30_days
            ).count(),
            'referrals_7_days': clinic.referred_users.filter(
                created_at__gte=last_7_days
            ).count(),
            'conversion_rate': self._calculate_conversion_rate(clinic),
        }
        
        # Referral code performance
        code_stats = []
        for code in clinic.referral_codes.all():
            referrals_count = code.referreduser_set.count()
            code_stats.append({
                'code': code.code,
                'referrals': referrals_count,
                'is_active': code.is_active,
            })
        
        context['code_stats'] = sorted(
            code_stats, 
            key=lambda x: x['referrals'], 
            reverse=True
        )
        
        return context
    
    def _calculate_conversion_rate(self, clinic):
        """Calculate conversion rate from referrals to active users"""
        total_referrals = clinic.referred_users.count()
        if total_referrals == 0:
            return 0
        
        active_users = clinic.referred_users.filter(
            status=ReferralStatus.ACTIVE
        ).count()
        
        return round((active_users / total_referrals) * 100, 1)


class ReferralLandingView(TemplateView):
    """Landing page for referral links - available after email confirmation"""
    template_name = 'vets/referral_landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        code = kwargs.get('code')
        
        try:
            referral_code = ReferralCode.objects.select_related('clinic').get(
                code=code,
                is_active=True
            )
            
            # Check if the clinic has confirmed their email
            # No need to wait for admin approval to start accepting referrals
            clinic = referral_code.clinic
            if not clinic.email_confirmed:
                raise Http404("This clinic is not currently accepting referrals")
            
            context['referral_code'] = referral_code
            context['clinic'] = clinic
            
            # Store referral code in session for later use
            self.request.session['referral_code'] = code
            
        except ReferralCode.DoesNotExist:
            raise Http404("Referral code not found or inactive")
        
        return context


@method_decorator(csrf_exempt, name='dispatch')
class TrackReferralAPIView(View):
    """API endpoint to track referral conversions"""
    
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            email = data.get('email')
            referral_code = data.get('referral_code')
            
            if not email or not referral_code:
                return JsonResponse({'error': 'Missing required fields'}, status=400)
            
            # Get referral code object
            try:
                ref_code_obj = ReferralCode.objects.get(
                    code=referral_code,
                    is_active=True
                )
            except ReferralCode.DoesNotExist:
                return JsonResponse({'error': 'Invalid referral code'}, status=400)
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
                user_exists = True
            except User.DoesNotExist:
                user = None
                user_exists = False
            
            # Create or update referred user record
            referred_user, created = ReferredUser.objects.get_or_create(
                clinic=ref_code_obj.clinic,
                referral_code=ref_code_obj,
                user=user,
                defaults={
                    'email_capture': email if not user_exists else '',
                    'status': ReferralStatus.ACTIVE if user_exists else ReferralStatus.NEW
                }
            )
            
            if not created and user_exists and not referred_user.user:
                # Update existing record with user
                referred_user.user = user
                referred_user.status = ReferralStatus.ACTIVE
                referred_user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Referral tracked successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def clinic_terms_and_conditions_view(request):
    """Display clinic terms and conditions"""
    return render(request, 'vets/clinic_terms_and_conditions.html')


def clinic_partnership_agreement_view(request):
    """Display clinic partnership agreement"""
    return render(request, 'vets/clinic_partnership_agreement.html')


# ========== Location & Nearby Clinics API ==========

class ClinicFinderView(TemplateView):
    """Main clinic finder page with location detection"""
    template_name = 'vets/clinic_finder.html'


class NearbyClinicAPIView(View):
    """API endpoint to find clinics near given coordinates"""
    
    def get(self, request, *args, **kwargs):
        try:
            # Get parameters
            lat = request.GET.get('lat')
            lng = request.GET.get('lng')
            radius = request.GET.get('radius', 50)  # Default 50km
            
            if not lat or not lng:
                return JsonResponse({
                    'error': 'Latitude and longitude are required'
                }, status=400)
            
            # Convert to float
            try:
                latitude = float(lat)
                longitude = float(lng)
                radius_km = float(radius)
            except ValueError:
                return JsonResponse({
                    'error': 'Invalid coordinate format'
                }, status=400)
            
            # Validate coordinates
            if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                return JsonResponse({
                    'error': 'Invalid coordinates'
                }, status=400)
            
            # Get nearby clinics
            from .utils import get_clinics_within_radius
            clinics = get_clinics_within_radius(latitude, longitude, radius_km)
            
            # Serialize clinic data
            clinic_data = []
            for clinic in clinics:
                clinic_data.append({
                    'id': clinic.id,
                    'name': clinic.name,
                    'slug': clinic.slug,
                    'city': clinic.city,
                    'address': clinic.address,
                    'phone': clinic.phone,
                    'email': clinic.email,
                    'website': clinic.website,
                    'working_hours': clinic.working_hours,
                    'specializations': clinic.specializations,
                    'latitude': float(clinic.latitude) if clinic.latitude else None,
                    'longitude': float(clinic.longitude) if clinic.longitude else None,
                    'distance': clinic.distance,
                    'is_verified': clinic.is_verified,
                    'logo': clinic.logo.url if clinic.logo else None,
                })
            
            return JsonResponse({
                'success': True,
                'count': len(clinic_data),
                'clinics': clinic_data,
                'search_params': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius_km': radius_km
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Server error: {str(e)}'
            }, status=500)


class ClinicsByCityAPIView(View):
    """API endpoint to find clinics by city name"""
    
    def get(self, request, *args, **kwargs):
        try:
            city = request.GET.get('city', '').strip()
            radius = request.GET.get('radius', 10)
            
            if not city:
                return JsonResponse({
                    'error': 'City name is required'
                }, status=400)
            
            # Search for clinics in the city
            clinics = Clinic.objects.filter(
                city__icontains=city,
                email_confirmed=True,
                admin_approved=True
            ).order_by('name')
            
            # Serialize clinic data
            clinic_data = []
            for clinic in clinics:
                clinic_data.append({
                    'id': clinic.id,
                    'name': clinic.name,
                    'slug': clinic.slug,
                    'city': clinic.city,
                    'address': clinic.address,
                    'phone': clinic.phone,
                    'email': clinic.email,
                    'website': clinic.website,
                    'working_hours': clinic.working_hours,
                    'specializations': clinic.specializations,
                    'latitude': float(clinic.latitude) if clinic.latitude else None,
                    'longitude': float(clinic.longitude) if clinic.longitude else None,
                    'is_verified': clinic.is_verified,
                    'logo': clinic.logo.url if clinic.logo else None,
                })
            
            return JsonResponse({
                'success': True,
                'count': len(clinic_data),
                'clinics': clinic_data,
                'search_params': {
                    'city': city,
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'error': f'Server error: {str(e)}'
            }, status=500)


class IPLocationAPIView(View):
    """API endpoint to get location from user's IP address"""
    
    def get(self, request, *args, **kwargs):
        try:
            from .utils import get_client_ip, get_location_from_ip
            
            ip_address = get_client_ip(request)
            location = get_location_from_ip(ip_address)
            
            if location:
                return JsonResponse({
                    'success': True,
                    'location': location,
                    'ip': ip_address
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Unable to determine location from IP',
                    'ip': ip_address
                }, status=404)
                
        except Exception as e:
            return JsonResponse({
                'error': f'Server error: {str(e)}'
            }, status=500)


@method_decorator(user_passes_test(lambda u: u.is_staff or u.is_superuser), name='dispatch')
class ClinicNearbyUsersReportView(TemplateView):
    """Admin-only report: users near a given clinic within a radius (km)."""
    template_name = 'vets/admin/nearby_users_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        clinic_id = kwargs.get('clinic_id')
        clinic = get_object_or_404(Clinic, id=clinic_id)
        radius_km = self.request.GET.get('radius', '10')
        try:
            radius_km = float(radius_km)
        except ValueError:
            radius_km = 10.0

        users = []
        if clinic.latitude is not None and clinic.longitude is not None:
            from .utils import haversine_distance
            # Only profiles with consent and coordinates
            qs = Profile.objects.filter(
                location_consent=True,
                latitude__isnull=False,
                longitude__isnull=False,
            ).select_related('user')
            for prof in qs:
                try:
                    dist = haversine_distance(
                        float(clinic.latitude), float(clinic.longitude),
                        float(prof.latitude), float(prof.longitude)
                    )
                except Exception:
                    continue
                if dist <= radius_km:
                    users.append({
                        'profile': prof,
                        'email': getattr(prof.user, 'email', ''),
                        'first_name': prof.first_name,
                        'last_name': prof.last_name,
                        'city': prof.city,
                        'distance_km': round(dist, 1),
                        'location_updated_at': prof.location_updated_at,
                    })
            users.sort(key=lambda x: x['distance_km'])

        context.update({
            'clinic': clinic,
            'radius_km': radius_km,
            'users': users,
            'clinic_has_coords': clinic.latitude is not None and clinic.longitude is not None,
        })
        return context

