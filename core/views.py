from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from .models import HeroSection, SocialLinks, FAQ, ContactMessage, Lead
from .forms import HeroSectionForm, SocialLinksForm, FAQForm, ContactForm
from pet.models import PetType
from django.contrib.auth.hashers import make_password
import string
import random

def home(request):
    # Get the currently active hero section
    hero_section = HeroSection.objects.filter(is_active=True).first()
    faqs = FAQ.objects.filter(is_published=True).order_by("sort_order", "-updated_at")
    
    # Dynamic placeholder for chat input
    chat_placeholder = "Hey, Need help with your cat or dog? Type here…"
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and getattr(profile, "first_name", None):
            first_name = profile.first_name.strip()
            if first_name:
                chat_placeholder = f"Hey {first_name}! What's your pet question today?"
    
    return render(request, 'core/home.html', {
        'hero': hero_section, 
        "faqs": faqs,
        "chat_placeholder": chat_placeholder
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_hero_section(request):
    # Get the first hero section instance, or create one if it doesn't exist
    hero_section, created = HeroSection.objects.get_or_create(
        id=1, 
        defaults={
            'heading': 'Default Heading',
            'subheading': 'Default subheading text.',
            'button_text': 'Get Started',
            'button_url': '#'
        }
    )
    
    if request.method == 'POST':
        form = HeroSectionForm(request.POST, request.FILES, instance=hero_section)
        if form.is_valid():
            form.save()
            messages.success(request, 'Hero section updated successfully!')
            return redirect('manage_hero_section')
    else:
        form = HeroSectionForm(instance=hero_section)
        
    return render(request, 'core/manage_hero_section.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_social_links(request):
    links, created = SocialLinks.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = SocialLinksForm(request.POST, instance=links)
        if form.is_valid():
            form.save()
            messages.success(request, "Social media links updated!")
            return redirect('manage_social_links')
    else:
        form = SocialLinksForm(instance=links)
    return render(request, 'core/manage_social_links.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff)
def manage_faqs(request):
    if request.method == "POST":
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "FAQ added!")
            return redirect("manage_faqs")
    else:
        form = FAQForm()
    items = FAQ.objects.order_by("sort_order", "-updated_at")
    return render(request, "core/manage_faqs.html", {"form": form, "items": items})

@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_faq(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    if request.method == "POST":
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            messages.success(request, "FAQ updated!")
            return redirect("manage_faqs")
    else:
        form = FAQForm(instance=faq)
    items = FAQ.objects.order_by("sort_order", "-updated_at")
    return render(request, "core/manage_faqs.html", {"form": form, "items": items, "edit_id": faq.id})

@login_required
@user_passes_test(lambda u: u.is_staff)
def delete_faq(request, pk):
    faq = get_object_or_404(FAQ, pk=pk)
    faq.delete()
    messages.success(request, "FAQ deleted.")
    return redirect("manage_faqs")

def contact(request):
    links = SocialLinks.objects.first()  # show social icons/links if you want
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            msg = form.save()
            # OPTIONAL: email notification to your inbox if SMTP is configured
            to_email = getattr(settings, "CONTACT_EMAIL", None)
            if to_email:
                try:
                    send_mail(
                        subject=f"[FAMO Contact] {msg.subject or 'New Message'}",
                        message=f"From: {msg.name} <{msg.email}>\n\n{msg.message}",
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or to_email,
                        recipient_list=[to_email],
                        fail_silently=True,
                    )
                except BadHeaderError:
                    pass

            messages.success(request, "Thanks! Your message has been sent.")
            return redirect("contact")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ContactForm()

    return render(request, "core/contact.html", {"form": form, "links": links})

import string
import random
from django.contrib.auth import get_user_model, login
from django.contrib.auth.hashers import make_password

def generate_secure_password():
    """Generate a secure random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()"
    length = 12
    return ''.join(random.choice(chars) for _ in range(length))

def collect_lead(request):
    """API endpoint to collect lead information from the home page form."""
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    
    pet_type = (request.POST.get("pet_type") or "").lower()
    weight = request.POST.get("weight")
    email = (request.POST.get("email") or "").strip().lower()
    
    print(f"Received form data - pet_type: {pet_type}, weight: {weight}, email: {email}")  # Debug log
    
    if pet_type not in ("cat","dog") or not weight or not email:
        return JsonResponse({"error": "Missing required fields"}, status=400)
    
    try:
        weight = float(weight)  # Convert weight to float
        if weight <= 0:
            return JsonResponse({"error": "Weight must be greater than 0"}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid weight value"}, status=400)

    # Check if user already exists
    User = get_user_model()
    user_exists = User.objects.filter(email=email).exists()
    generated_password = None

    # Generate password only for new users
    if not user_exists:
        generated_password = generate_secure_password()
        
    try:
        lead = Lead.objects.create(pet_type=pet_type, weight=weight, email=email)
        print(f"Created lead with UUID: {lead.uuid}")  # Debug log

        # Create user account if email doesn't exist
        if not user_exists and generated_password:
            # Get the user model and create a new user
            user = User.objects.create_user(
                email=email,
                password=generated_password,
            )
            # Activate the user immediately since they're coming through the lead funnel
            user.is_active = True
            user.backend = 'django.contrib.auth.backends.ModelBackend'  # Set the backend
            user.save()
            print(f"Created new user account for: {email}")
    except Exception as e:
        print(f"Error creating lead or user: {str(e)}")  # Debug log
        return JsonResponse({"error": str(e)}, status=500)

    # Email CTA → starts the flow with this lead UUID
    cta_url = request.build_absolute_uri(reverse("core:start_from_lead", args=[lead.uuid]))
    subject = "Your FAMO Pet Profile is Ready!"
    
    if generated_password:
        body = (
            "Welcome to FAMO!\n\n"
            "We've created your account to get started with your pet's personalized plan.\n\n"
            f"Your login credentials:\n"
            f"Email: {email}\n"
            f"Password: {generated_password}\n\n"
            f"Click here to access your pet's profile (you'll be automatically logged in):\n"
            f"{cta_url}\n\n"
            "For security, please change your password after logging in.\n\n"
            "— FAMMO.ai"
        )
    else:
        body = (
            "Welcome back to FAMO!\n\n"
            "We've updated your pet's personalized plan.\n\n"
            f"Click here to view your pet's profile:\n{cta_url}\n\n"
            "— FAMMO.ai"
        )
    
    print(f"Attempting to send email to {email} with CTA URL: {cta_url}")  # Debug log
    
    try:
        result = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False  # Changed to False to see errors
        )
        print(f"Email sent successfully: {result}")  # Debug log
    except Exception as e:
        print(f"Error sending email: {str(e)}")  # Debug log
        # We don't return an error here because the lead was created successfully
        
    return JsonResponse({"ok": True, "uuid": lead.uuid})

from django.contrib.auth import get_user_model, login, authenticate
from django.contrib.auth.backends import ModelBackend

def start_from_lead(request, uuid):
    """Process lead link and handle auto-login for new users."""
    lead = Lead.objects.filter(uuid=uuid).first()
    if not lead:
        messages.error(request, "Invalid or expired link.")
        return HttpResponseRedirect(reverse("core:home"))
        
    # Store lead info in session
    request.session['lead_email'] = lead.email
    request.session['lead_pet_type'] = lead.pet_type
    request.session['lead_weight'] = float(lead.weight)
    request.session['lead_uuid'] = lead.uuid
    request.session.modified = True
    
    # Check if user exists and handle authentication
    User = get_user_model()
    try:
        user = User.objects.get(email=lead.email)
        
        # If user is not logged in, authenticate and log them in
        if not request.user.is_authenticated:
            # First try to authenticate using the ModelBackend
            authenticated_user = authenticate(request, username=lead.email, email=lead.email)
            if authenticated_user:
                login(request, authenticated_user, backend='django.contrib.auth.backends.ModelBackend')
            else:
                # If ModelBackend fails, use the Allauth backend
                login(request, user, backend='allauth.account.auth_backends.AuthenticationBackend')
                
            messages.success(request, "Welcome back! You've been automatically logged in.")
            
        # Redirect to pet wizard
        return HttpResponseRedirect(reverse('pet:pet_wizard'))
        
    except User.DoesNotExist:
        # If user doesn't exist, redirect to signup
        # (shouldn't happen normally as we create users in collect_lead)
        messages.info(request, "Please sign up to continue.")
        return HttpResponseRedirect(reverse('account_signup'))
    else:
        # New user - redirect to signup
        signup_url = reverse("account_signup")
        messages.info(request, "Please create an account to continue setting up your pet's profile.")
        return HttpResponseRedirect(f"{signup_url}?next={next_url}")