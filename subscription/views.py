from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from subscription.models import SubscriptionPlan

@login_required
def subscription_plans_view(request):
    plans = SubscriptionPlan.objects.all().order_by('price_eur')

    if request.method == "POST":
        selected_plan_id = request.POST.get("plan_id")
        if selected_plan_id:
            plan = SubscriptionPlan.objects.get(id=selected_plan_id)
            profile = request.user.profile
            profile.subscription_plan = plan
            profile.save()
            return redirect("my_pets")  # or any success page

    return render(request, "subscription/plan_list.html", {
        "plans": plans,
        "current_plan": request.user.profile.subscription_plan,
    })
