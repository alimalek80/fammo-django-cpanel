import openai
import json
from openai import OpenAI
from pydantic import BaseModel
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from pet.models import Pet
from .models import AIRecommendation, RecommendationType, AIHealthReport
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from datetime import datetime, timedelta
from django.utils.timezone import now
from subscription.models import AIUsage, first_day_of_current_month
from django.utils.translation import gettext_lazy as _


openai.api_key = settings.OPENAI_API_KEY

# Pydantic models for Structured Outputs
class NutrientTargets(BaseModel):
    protein_percent: str
    fat_percent: str
    carbs_percent: str

class MealSection(BaseModel):
    title: str
    items: list[str]

class MealOption(BaseModel):
    name: str
    overview: str
    sections: list[MealSection]

class FeedingSchedule(BaseModel):
    time: str
    note: str

class MealPlan(BaseModel):
    der_kcal: int
    nutrient_targets: NutrientTargets
    options: list[MealOption]
    feeding_schedule: list[FeedingSchedule]
    safety_notes: list[str]

class HealthReport(BaseModel):
    health_summary: str
    breed_risks: list[str]
    weight_and_diet: str
    feeding_tips: list[str]
    activity: str
    alerts: list[str]

def generate_meal_recommendation(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, user=request.user)

    # Limit: 3 per user per month
    start_of_month = datetime(now().year, now().month, 1)
    used_count = AIRecommendation.objects.filter(
        pet__user=request.user,
        type=RecommendationType.MEAL,
        created_at__gte=start_of_month
    ).count()

    # Get the user's assigned plan from profile
    user_profile = request.user.profile
    meal_limit = user_profile.subscription_plan.monthly_meal_limit if user_profile.subscription_plan else 3

    if not request.user.is_superuser and used_count >= meal_limit:
        return render(request, 'aihub/limit_reached.html', {
            'message': _("You’ve reached your monthly limit of %(limit)s AI meal suggestions.") % {"limit": meal_limit}
        })

    pet_profile = pet.get_full_profile_for_ai()
    # Ask for structured meal plan
    prompt = (
        "You are a professional pet nutritionist. Based on the pet profile below, generate a detailed one-day meal plan. "
        "Provide practical, safe, and nutritionally appropriate recommendations.\n\n"
        f"Pet Profile:\n{pet_profile}"
    )
    
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=prompt,
        text_format=MealPlan,
    )

    # Get parsed output
    meal_plan = response.output_parsed
    # Convert to dict for JSON storage
    content_json = meal_plan.model_dump() if meal_plan else None
    # Also keep text representation
    result = json.dumps(content_json, indent=2) if content_json else ""

    ip_address = get_client_ip(request)
    recommendation = AIRecommendation.objects.create(
        pet=pet,
        type=RecommendationType.MEAL,
        content=result,
        content_json=content_json,
        ip_address=ip_address  # Save IP
    )

    # Only track usage for normal users
    if not request.user.is_superuser:
        from subscription.models import AIUsage, first_day_of_current_month

        usage, created = AIUsage.objects.get_or_create(
            user=request.user,
            month=first_day_of_current_month()
        )
        usage.meal_used += 1
        usage.save()

    return render(request, 'aihub/meal_result.html', {
        'recommendation': recommendation,
        'pet': pet
    })

def generate_health_report(request, pet_id):
    pet = get_object_or_404(Pet, id=pet_id, user=request.user)

    start_of_month = datetime(now().year, now().month, 1)
    used_count = AIHealthReport.objects.filter(
        pet__user=request.user,
        created_at__gte=start_of_month
    ).count()

    user_profile = request.user.profile
    health_limit = user_profile.subscription_plan.monthly_health_limit if user_profile.subscription_plan else 1

    if not request.user.is_superuser and used_count >= health_limit:
        return render(request, 'aihub/limit_reached.html', {
            'message': _("You’ve reached your monthly limit of %(limit)s AI health reports.") % {"limit": health_limit}
        })

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    pet_profile = pet.get_full_profile_for_ai()
    prompt = (
        "You are a professional pet health consultant. Based on the pet profile below, generate a comprehensive health insight report. "
        "Be informative, concise, and provide actionable recommendations.\n\n"
        f"Pet Profile:\n{pet_profile}"
    )

    response = client.responses.parse(
        model="gpt-4o-2024-08-06",
        input=prompt,
        text_format=HealthReport,
    )

    # Get parsed output
    health_data = response.output_parsed
    # Convert to dict for JSON storage
    summary_json = health_data.model_dump() if health_data else None
    # Also keep text representation
    result = json.dumps(summary_json, indent=2) if summary_json else ""

    ip_address = get_client_ip(request)
    report = AIHealthReport.objects.create(
        pet=pet,
        summary=result,
        summary_json=summary_json,
        ip_address=ip_address  # Save IP
    )

    if not request.user.is_superuser:
        usage, created = AIUsage.objects.get_or_create(
            user=request.user,
            month=first_day_of_current_month()
        )
        usage.health_used += 1
        usage.save()

    return render(request, 'aihub/health_report.html', {
        'report': report,
        'pet': pet
    })

@method_decorator(login_required, name='dispatch')
class AIHistoryView(TemplateView):
    template_name = 'aihub/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_pets = self.request.user.pets.all()
        context['user_pets'] = user_pets  # <-- Add this line
        context['recommendations'] = AIRecommendation.objects.filter(pet__in=user_pets).order_by('-created_at')
        context['reports'] = AIHealthReport.objects.filter(pet__in=user_pets).order_by('-created_at')
        return context

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip