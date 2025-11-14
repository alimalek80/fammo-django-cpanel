from subscription.models import AIUsage, first_day_of_current_month

def ai_usage_status(request):
    if not request.user.is_authenticated:
        return {}

    try:
        usage = request.user.ai_usages.get(month=first_day_of_current_month())
    except:
        usage = None

    plan = getattr(request.user.profile, "subscription_plan", None)
    return {
        'user_meal_used': usage.meal_used if usage else 0,
        'user_meal_limit': plan.monthly_meal_limit if plan else 3,
        'user_health_used': usage.health_used if usage else 0,
        'user_health_limit': plan.monthly_health_limit if plan else 1,
    }
