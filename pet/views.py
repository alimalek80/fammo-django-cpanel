from django.shortcuts import render, redirect, get_object_or_404
from .forms import PetForm, Step1NameForm, Step2GenderForm, Step3AgeForm, Step4BreedForm, Step5FoodForm, Step6FoodFeelingForm, Step7FoodImportanceForm, Step8BodyTypeForm, Step9WeightForm, Step10ActivityLevelForm, Step11FoodAllergiesForm, Step12HealthIssuesForm, Step13TreatFrequencyForm, Step14EmailForm, Step15AccountChoiceForm
from .models import Pet
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import Breed, PetType, AgeCategory
from django.contrib import messages
import csv
from django.http import HttpResponse
from formtools.wizard.views import SessionWizardView
from core.models import Lead


@login_required
def pet_form_view(request, pk=None):
    if pk:
        pet = get_object_or_404(Pet, pk=pk, user=request.user)
    else:
        pet = None

    # --- LIMITATION LOGIC: Only when adding a new pet ---
    if not pet:  # Only check limit when adding, not editing
        user = request.user
        if not user.is_staff:
            profile = getattr(user, 'profile', None)
            plan = getattr(profile, 'subscription_plan', None)
            if plan:
                pet_limit = plan.pet_limit() if hasattr(plan, 'pet_limit') else 1
                current_pet_count = Pet.objects.filter(user=user).count()
                if current_pet_count >= pet_limit:
                    messages.error(request, f"You can only add up to {pet_limit} pets with your current plan.")
                    return redirect('pet:my_pets')

    if request.method == 'POST':
        form = PetForm(request.POST, instance=pet)
        if form.is_valid():
            new_pet = form.save(commit=False)
            new_pet.user = request.user
            new_pet.save()
            form.save_m2m()
            return redirect('pet:my_pets')  # Replace with your pets list view name
    else:
        form = PetForm(instance=pet)

    # Get PetType objects for Cat and Dog
    cat_type = PetType.objects.filter(name__iexact='Cat').first()
    dog_type = PetType.objects.filter(name__iexact='Dog').first()
    cat_ages = AgeCategory.objects.filter(pet_type=cat_type) if cat_type else []
    dog_ages = AgeCategory.objects.filter(pet_type=dog_type) if dog_type else []

    context = {
        'form': form,
        'is_edit': bool(pet),
        'cat_ages': cat_ages,
        'dog_ages': dog_ages,
    }
    return render(request, 'pet/pet_form.html', context)

def load_breeds(request):
    pet_type_id = request.GET.get('pet_type')
    breeds = Breed.objects.filter(pet_type_id=pet_type_id).order_by('name')
    return JsonResponse(list(breeds.values('id', 'name')), safe=False)

def my_pets_view(request):
    if not request.user.is_authenticated:
        messages.info(request, "Please log in to view your pets.")
        return redirect('login')  # Use your login URL name
    pets = request.user.pets.all()
    return render(request, 'pet/my_pets.html', {'pets': pets})

@login_required
def delete_pet_view(request, pk):
    pet = get_object_or_404(Pet, pk=pk, user=request.user)
    
    if request.method == "POST":
        pet.delete()
        return redirect('pet:my_pets')
    
    # If somehow accessed via GET (not expected), redirect safely
    return redirect('pet:my_pets')

@login_required
def pet_detail_view(request, pk):
    pet = get_object_or_404(Pet, pk=pk, user=request.user)
    return render(request, 'pet/pet_detail.html', {'pet': pet})

@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def export_pets_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pets.csv"'

    writer = csv.writer(response)
    # Write header (all fields)
    writer.writerow([
        'ID', 'Name', 'User Email', 'Type', 'Gender', 'Neutered', 'Age Category',
        'Age (years)', 'Age (months)', 'Age (weeks)', 'Breed', 'Food Types',
        'Food Feeling', 'Food Importance', 'Body Type', 'Weight', 'Activity Level',
        'Food Allergies', 'Other Food Allergy', 'Health Issues', 'Treat Frequency'
    ])
    # Write data
    for pet in Pet.objects.select_related(
        'user', 'pet_type', 'gender', 'age_category', 'breed', 'food_feeling',
        'food_importance', 'body_type', 'activity_level', 'treat_frequency'
    ).prefetch_related('food_types', 'food_allergies', 'health_issues').all():
        writer.writerow([
            pet.id,
            pet.name,
            pet.user.email,
            pet.pet_type.name if pet.pet_type else '',
            pet.gender.name if pet.gender else '',
            'Yes' if pet.neutered else 'No',
            pet.age_category.name if pet.age_category else '',
            pet.age_years or '',
            pet.age_months or '',
            pet.age_weeks or '',
            pet.breed.name if pet.breed else '',
            ', '.join([ft.name for ft in pet.food_types.all()]),
            pet.food_feeling.name if pet.food_feeling else '',
            pet.food_importance.name if pet.food_importance else '',
            pet.body_type.name if pet.body_type else '',
            pet.weight or '',
            pet.activity_level.name if pet.activity_level else '',
            ', '.join([fa.name for fa in pet.food_allergies.all()]),
            pet.food_allergy_other or '',
            ', '.join([hi.name for hi in pet.health_issues.all()]),
            pet.treat_frequency.name if pet.treat_frequency else '',
        ])
    return response


# ============================================================================
# NEW WIZARD IMPLEMENTATION USING SESSIONWIZARDVIEW (Step by step)
# ============================================================================

# Start with Step 1, Step 2, Step 3, Step 4, Step 5, and Step 6
FORMS = [
    ("step1", Step1NameForm),
    ("step2", Step2GenderForm),
    ("step3", Step3AgeForm),
    ("step4", Step4BreedForm),
    ("step5", Step5FoodForm),
    ("step6", Step6FoodFeelingForm),
    ("step7", Step7FoodImportanceForm),
    ("step8", Step8BodyTypeForm),
    ("step9", Step9WeightForm),
    ("step10", Step10ActivityLevelForm),
    ("step11", Step11FoodAllergiesForm),
    ("step12", Step12HealthIssuesForm),
    ("step13", Step13TreatFrequencyForm),
    ("step14", Step14EmailForm),
    ("step15", Step15AccountChoiceForm),
]

# Conditional logic for showing steps only to non-logged-in users
CONDITION_DICT = {
    "step14": lambda wizard: not wizard.request.user.is_authenticated,
    "step15": lambda wizard: not wizard.request.user.is_authenticated,
}

class PetWizard(SessionWizardView):
    form_list = dict(FORMS)
    condition_dict = CONDITION_DICT
    template_name = "pet/wizard_step.html"
    
    def get_form_kwargs(self, step=None):
        """Pass wizard instance to forms that need it"""
        kwargs = super().get_form_kwargs(step)
        if step in ['step2', 'step3', 'step4', 'step5', 'step6', 'step7', 'step8', 'step9', 'step10', 'step11', 'step12', 'step13', 'step14', 'step15']:  # Forms that need wizard instance
            kwargs['wizard'] = self
        return kwargs
        
    def _lead(self):
        """Get the lead from session if it exists"""
        uuid = self.request.session.get("lead_uuid")
        if not uuid:
            return None
        return Lead.objects.filter(uuid=uuid).first()

    def get_form_initial(self, step):
        """Pre-fill form data from the lead if available"""
        initial = super().get_form_initial(step)
        lead = self._lead()
        if not lead:
            return initial

        # Map 'cat'/'dog' to PetType if available
        if step == "step1":
            pt = PetType.objects.filter(name__iexact=lead.pet_type).first()
            if pt:
                initial.update({"pet_type": pt.id})

        if step == "step9":
            initial.update({"weight": lead.weight})

        return initial

    def done(self, form_list, **kwargs):
        """Process the wizard completion"""
        # Mark lead as processed if it exists
        lead = self._lead()
        if lead:
            lead.processed = True
            lead.save(update_fields=["processed"])
            # Clear the lead from session
            if "lead_uuid" in self.request.session:
                del self.request.session["lead_uuid"]
                self.request.session.modified = True
        
        return super().done(form_list, **kwargs)
    
    def get_form(self, step=None, data=None, files=None):
        """Handle invalid choice issues when user changes pet type and navigates back"""
        
        # Handle step3 age_category invalid choice issue
        if step == 'step3' and data:
            # Get current pet type from step1
            step1_data = self.get_cleaned_data_for_step('step1') or {}
            current_pet_type = step1_data.get('pet_type')
            
            if current_pet_type:
                # Check if the age_category in the form data is valid for current pet_type
                age_category_id = data.get('step3-age_category')
                if age_category_id:
                    try:
                        from .models import AgeCategory
                        age_category = AgeCategory.objects.get(pk=age_category_id)
                        if age_category.pet_type != current_pet_type:
                            # Remove invalid age category from form data
                            data = data.copy()
                            data.pop('step3-age_category', None)
                            # Also clear related age fields
                            data.pop('step3-age_years', None) 
                            data.pop('step3-age_months', None)
                            data.pop('step3-age_weeks', None)
                    except (AgeCategory.DoesNotExist, ValueError):
                        # Invalid ID, remove it
                        data = data.copy()
                        data.pop('step3-age_category', None)
                        data.pop('step3-age_years', None)
                        data.pop('step3-age_months', None) 
                        data.pop('step3-age_weeks', None)
        
        # Handle step4 breed invalid choice issue
        if step == 'step4' and data:
            # Get current pet type from step1
            step1_data = self.get_cleaned_data_for_step('step1') or {}
            current_pet_type = step1_data.get('pet_type')
            
            if current_pet_type:
                # Check if the breed in the form data is valid for current pet_type
                breed_id = data.get('step4-breed')
                if breed_id:
                    try:
                        from .models import Breed
                        breed = Breed.objects.get(pk=breed_id)
                        if breed.pet_type != current_pet_type:
                            # Remove invalid breed from form data
                            data = data.copy()
                            data.pop('step4-breed', None)
                            # Don't clear unknown_breed as user might want to keep that selection
                    except (Breed.DoesNotExist, ValueError):
                        # Invalid ID, remove it
                        data = data.copy()
                        data.pop('step4-breed', None)
        
        return super().get_form(step, data, files)
    
    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        current_step = int(self.steps.current.replace('step', ''))
        total_steps = len(self.form_list)
        
        # Calculate progress: 0% for step 1, then incremental progress
        # This gives better UX: Step 1 = 0%, Step 2 = 50%, completion = 100%
        if current_step == 1:
            progress_percent = 0
        else:
            progress_percent = int(((current_step - 1) / total_steps) * 100)
        
        context.update({
            'step_number': current_step,
            'step_total': total_steps,
            'progress_percent': progress_percent,
        })
        return context
    
    def done(self, form_list, **kwargs):
        """Called when all forms are valid - handle different flows based on user authentication"""
        from userapp.models import CustomUser, Profile
        from subscription.models import SubscriptionPlan
        from django.core.mail import send_mail
        from django.contrib.sites.shortcuts import get_current_site
        from django.template.loader import render_to_string
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth import login
        
        # Collect data from all forms
        form_data = {}
        for form in form_list:
            form_data.update(form.cleaned_data)
        
        # Check if user is logged in
        if self.request.user.is_authenticated:
            # LOGGED-IN USER FLOW: Create pet and save to their account
            pet = Pet(user=self.request.user)
            pet.name = form_data.get('name')
            pet.pet_type = form_data.get('pet_type')
            pet.gender = form_data.get('gender')
            pet.neutered = form_data.get('neutered')
            pet.age_category = form_data.get('age_category')
            pet.age_years = form_data.get('age_years')
            pet.age_months = form_data.get('age_months')
            pet.age_weeks = form_data.get('age_weeks')
            pet.breed = form_data.get('breed')
            pet.unknown_breed = form_data.get('unknown_breed')
            pet.food_feeling = form_data.get('food_feeling')
            pet.food_importance = form_data.get('food_importance')
            pet.body_type = form_data.get('body_type')
            pet.weight = form_data.get('weight')
            pet.activity_level = form_data.get('activity_level')
            pet.food_allergy_other = form_data.get('food_allergy_other')
            pet.treat_frequency = form_data.get('treat_frequency')
            pet.save()
            
            # Handle many-to-many fields after saving the pet
            food_types = form_data.get('food_types')
            if food_types:
                pet.food_types.set(food_types)
            
            food_allergies = form_data.get('food_allergies')
            if food_allergies:
                pet.food_allergies.set(food_allergies)
            
            health_issues = form_data.get('health_issues')
            if health_issues:
                pet.health_issues.set(health_issues)
            
            messages.success(self.request, f"🎉 {pet.name} has been successfully added!")
            return redirect('pet:my_pets')
        
        else:
            # NON-LOGGED-IN USER FLOW: Handle based on their choice
            user_email = form_data.get('email')
            account_choice = form_data.get('account_choice')
            
            if account_choice == 'create_account':
                # CREATE ACCOUNT FLOW: Create user account with proper integration
                try:
                    # Check if user already exists
                    existing_user = CustomUser.objects.filter(email=user_email).first()
                    if existing_user:
                        if existing_user.is_active:
                            # User exists and is active - show message and stay on page
                            messages.error(self.request, f"⚠️ An account with {user_email} already exists. Please log in to your existing account or use a different email address.")
                            # Return to the same wizard step so user can correct the email
                            return self.render_goto_step(self.steps.current)
                        else:
                            # User exists but not activated - resend activation email
                            current_site = get_current_site(self.request)
                            subject = "Activate your FAMO account - Complete your pet profile"
                            message = render_to_string('userapp/account_activation_email.html', {
                                'user': existing_user,
                                'domain': current_site.domain,
                                'uid': urlsafe_base64_encode(force_bytes(existing_user.pk)),
                                'token': default_token_generator.make_token(existing_user),
                                'pet_name': form_data.get('name'),
                                'is_pet_registration': True,
                            })
                            send_mail(subject, message, None, [user_email], fail_silently=False)  # Use DEFAULT_FROM_EMAIL and show errors
                            
                            messages.info(self.request, f"📧 We've sent a new activation email to {user_email}. Please check your email to activate your account and complete {form_data.get('name')}'s profile.")
                            return redirect('/')
                    else:
                        # Create new user account using the proper registration flow
                        # Generate a random password for now (user will set it via email confirmation)
                        import secrets
                        temporary_password = secrets.token_urlsafe(12)
                        
                        user = CustomUser.objects.create_user(
                            email=user_email,
                            password=temporary_password
                        )
                        user.is_active = False  # User must confirm email first
                        user.save()
                        
                        # Profile is automatically created by Django signal, just get it and update if needed
                        try:
                            profile = Profile.objects.get(user=user)
                            # Update subscription plan if desired (or keep the default 'free' plan)
                            essentials_plan = SubscriptionPlan.objects.filter(name='essentials').first()
                            if essentials_plan:
                                profile.subscription_plan = essentials_plan
                                profile.save()
                        except Profile.DoesNotExist:
                            # Fallback: create profile if signal didn't work for some reason
                            default_plan = SubscriptionPlan.objects.filter(name='essentials').first()
                            if not default_plan:
                                default_plan = SubscriptionPlan.objects.filter(name='free').first()
                            
                            Profile.objects.create(
                                user=user,
                                first_name='',
                                last_name='',
                                phone='',
                                address='',
                                city='',
                                zip_code='',
                                country='',
                                subscription_plan=default_plan
                            )
                        
                        # Store pet data in session temporarily until user activates account
                        self.request.session[f'pending_pet_data_{user.pk}'] = {
                            'name': form_data.get('name'),
                            'pet_type_id': form_data.get('pet_type').pk if form_data.get('pet_type') else None,
                            'gender_id': form_data.get('gender').pk if form_data.get('gender') else None,
                            'neutered': form_data.get('neutered'),
                            'age_category_id': form_data.get('age_category').pk if form_data.get('age_category') else None,
                            'age_years': form_data.get('age_years'),
                            'age_months': form_data.get('age_months'),
                            'age_weeks': form_data.get('age_weeks'),
                            'breed_id': form_data.get('breed').pk if form_data.get('breed') else None,
                            'unknown_breed': form_data.get('unknown_breed'),
                            'food_feeling_id': form_data.get('food_feeling').pk if form_data.get('food_feeling') else None,
                            'food_importance_id': form_data.get('food_importance').pk if form_data.get('food_importance') else None,
                            'body_type_id': form_data.get('body_type').pk if form_data.get('body_type') else None,
                            'weight': str(form_data.get('weight')) if form_data.get('weight') else None,
                            'activity_level_id': form_data.get('activity_level').pk if form_data.get('activity_level') else None,
                            'food_allergy_other': form_data.get('food_allergy_other'),
                            'treat_frequency_id': form_data.get('treat_frequency').pk if form_data.get('treat_frequency') else None,
                            'food_types_ids': [ft.pk for ft in form_data.get('food_types', [])],
                            'food_allergies_ids': [fa.pk for fa in form_data.get('food_allergies', [])],
                            'health_issues_ids': [hi.pk for hi in form_data.get('health_issues', [])],
                        }
                        
                        # Create the pet immediately (don't wait for activation)
                        pet = self._create_pet_from_form_data(user, form_data)
                        print(f"✅ Pet '{pet.name}' created immediately for inactive user {user.email}")  # Debug log
                        
                        # Send activation email with pet information
                        current_site = get_current_site(self.request)
                        subject = f"Activate your FAMO account - Complete {form_data.get('name')}'s profile"
                        message = render_to_string('userapp/account_activation_email.html', {
                            'user': user,
                            'domain': current_site.domain,
                            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                            'token': default_token_generator.make_token(user),
                            'pet_name': form_data.get('name'),
                            'is_pet_registration': True,
                        })
                        send_mail(subject, message, None, [user_email], fail_silently=False)
                        
                        messages.success(self.request, f"📧 Account created! We've sent an activation email to {user_email}. Please check your email to activate your account and complete {form_data.get('name')}'s profile.")
                        return redirect('/')
                        
                except Exception as e:
                    messages.error(self.request, f"Error creating account: {str(e)}")
                    # Return to the same wizard step so user can try again
                    return self.render_goto_step(self.steps.current)
            
            else:
                # TEST REPORT ONLY FLOW: Send email report without creating account
                try:
                    # Generate and send email report
                    pet_name = form_data.get('name')
                    email_context = {
                        'pet_name': pet_name,
                        'pet_type': form_data.get('pet_type'),
                        'weight': form_data.get('weight'),
                        'activity_level': form_data.get('activity_level'),
                        'food_types': form_data.get('food_types'),
                        'food_allergies': form_data.get('food_allergies'),
                        'user_email': user_email,
                    }
                    
                    # Send basic report email
                    subject = f"Your Pet Report for {pet_name} - FAMO-PET"
                    message = f"""
                    Thank you for using FAMO-PET!
                    
                    Here's the basic report for {pet_name}:
                    
                    Pet Details:
                    - Name: {pet_name}
                    - Type: {form_data.get('pet_type')}
                    - Weight: {form_data.get('weight')} kg
                    - Activity Level: {form_data.get('activity_level')}
                    
                    Food Information:
                    - Food Types: {', '.join([ft.name for ft in form_data.get('food_types', [])])}
                    - Food Allergies: {', '.join([fa.name for fa in form_data.get('food_allergies', [])])}
                    
                    Based on this information, we recommend consulting with a veterinarian for personalized nutrition advice.
                    
                    To get full detailed reports and save your pet's profile, consider creating an account at our website.
                    
                    Best regards,
                    FAMO-PET Team
                    """
                    
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=None,
                        recipient_list=[user_email],
                        fail_silently=False,
                    )
                    
                    messages.success(self.request, f"📧 Test report for {pet_name} has been sent to {user_email}!")
                    return redirect('/')
                    
                except Exception as e:
                    messages.error(self.request, f"Error sending report: {str(e)}")
                    return redirect('/')
    
    def _create_pet_from_form_data(self, user, form_data):
        """Helper method to create a pet from form data"""
        pet = Pet(user=user)
        pet.name = form_data.get('name')
        pet.pet_type = form_data.get('pet_type')
        pet.gender = form_data.get('gender')
        pet.neutered = form_data.get('neutered')
        pet.age_category = form_data.get('age_category')
        pet.age_years = form_data.get('age_years')
        pet.age_months = form_data.get('age_months')
        pet.age_weeks = form_data.get('age_weeks')
        pet.breed = form_data.get('breed')
        pet.unknown_breed = form_data.get('unknown_breed')
        pet.food_feeling = form_data.get('food_feeling')
        pet.food_importance = form_data.get('food_importance')
        pet.body_type = form_data.get('body_type')
        pet.weight = form_data.get('weight')
        pet.activity_level = form_data.get('activity_level')
        pet.food_allergy_other = form_data.get('food_allergy_other')
        pet.treat_frequency = form_data.get('treat_frequency')
        pet.save()
        
        # Handle many-to-many fields after saving the pet
        food_types = form_data.get('food_types')
        if food_types:
            pet.food_types.set(food_types)
        
        food_allergies = form_data.get('food_allergies')
        if food_allergies:
            pet.food_allergies.set(food_allergies)
        
        health_issues = form_data.get('health_issues')
        if health_issues:
            pet.health_issues.set(health_issues)
        
        return pet


