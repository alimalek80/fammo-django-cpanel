from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .ai_service import pet_answer
from pet.models import Pet

@require_http_methods(["GET", "POST"])
def chat(request):
    # reset chat if ?new=1
    if request.GET.get("new") == "1":
        request.session["history"] = []
        request.session.modified = True
        return redirect("chat")
    
    # keep a tiny convo history in session
    history = request.session.get("history", [])

    # Personalization context
    user_first = None
    pet_profiles = None
    primary_pet = None

    if request.user.is_authenticated:
        # best-effort first name (prefer Profile.first_name from custom user app)
        profile = getattr(request.user, "profile", None)
        if profile and getattr(profile, "first_name", None):
            user_first = (profile.first_name or "").strip()
        else:
            # fallback to username or email localpart
            username_like = getattr(request.user, "username", None) or getattr(request.user, "email", "")
            user_first = (username_like or "").split("@")[0]
        # fetch user's pets
        pets_qs = Pet.objects.filter(user=request.user).select_related(
            "pet_type", "breed", "gender", "age_category", "body_type", "activity_level", "food_feeling", "food_importance", "treat_frequency"
        ).prefetch_related("food_types", "food_allergies", "health_issues")
        pets = list(pets_qs)
        if pets:
            primary_pet = pets[0]
            # build profiles string (for multiple pets include all)
            parts = []
            for idx, p in enumerate(pets, start=1):
                parts.append(f"Pet {idx}:\n" + p.get_full_profile_for_ai())
            pet_profiles = "\n\n".join(parts)

    if request.method == "POST":
        user_msg = (request.POST.get("message") or "").strip()
        image_data = (request.POST.get("image_data") or "").strip()
        
        if not user_msg and not image_data:
            return render(request, "chat/chat.html", {
                "history": history,
                "error": "Please type a question or upload an image.",
                "user_first": user_first,
                "primary_pet": primary_pet,
            })

        # Append user message (with optional image)
        user_message = {"role": "user", "text": user_msg}
        if image_data:
            user_message["image_url"] = f"data:{image_data}" if not image_data.startswith("data:") else image_data
        history.append(user_message)

        # Check if this is the first user message (history was empty before appending)
        is_first_message = len(history) == 1

        # If not logged in, only answer the first question, then require login/register for more
        if not request.user.is_authenticated:
            login_url = reverse('login')
            register_url = reverse('register')
            if is_first_message:
                # Normal AI answer + suggestion (with optional image analysis)
                bot_reply = pet_answer(user_msg, user_name=user_first, pet_profiles=pet_profiles, is_first_message=is_first_message, image_base64=image_data or None)
                suggestion_html = (
                    "Tip: You can sign in to personalize answers for your pet. "
                    f"<a class=\"underline text-blue-400 hover:text-blue-300\" href=\"{login_url}\">Login</a> | "
                    f"<a class=\"underline text-blue-400 hover:text-blue-300\" href=\"{register_url}\">Register</a>"
                )
                bot_message = {"role": "bot", "text": bot_reply, "suggestion_html": suggestion_html}
            else:
                # Fixed message, no API call
                fixed_html = (
                    "To continue, please <a class=\"underline text-blue-400 hover:text-blue-300\" href=\"{login_url}\">login</a> or "
                    f"<a class=\"underline text-blue-400 hover:text-blue-300\" href=\"{register_url}\">register</a>. "
                    "This feature is for registered users only."
                )
                bot_message = {"role": "bot", "text": "", "suggestion_html": fixed_html}
            history.append(bot_message)
            request.session["history"] = history
            request.session.modified = True
            return redirect("chat")

        # If logged in, normal flow with suggestions (profile/pet)
        bot_reply = pet_answer(user_msg, user_name=user_first, pet_profiles=pet_profiles, is_first_message=is_first_message, image_base64=image_data or None)

        suggestion_html = None
        try:
            suggestion_shown = request.session.get("chat_suggestion_shown", False)
            suggestion_html_lines = []

            # Profile completeness
            profile = getattr(request.user, "profile", None)
            def _is_profile_complete(p):
                if not p:
                    return False
                required = [
                    'first_name','last_name','phone','address','city','zip_code','country'
                ]
                for field in required:
                    val = getattr(p, field, '') or ''
                    if not str(val).strip():
                        return False
                return True

            if not _is_profile_complete(profile):
                profile_url = reverse('update_profile')
                suggestion_html_lines.append(
                    (
                        "Quick suggestion: complete your profile so I can address you properly and consider your location. "
                        f"<a class=\"underline text-blue-400 hover:text-blue-300\" href=\"{profile_url}\">Update profile</a>"
                    )
                )

            # Pet profiles
            has_pets = Pet.objects.filter(user=request.user).exists()
            if not has_pets:
                create_pet_url = reverse('pet:create_pet')
                wizard_url = reverse('pet:pet_wizard')
                suggestion_html_lines.append(
                    (
                        "For more tailored tips, add your pet’s profile. "
                        f"<a class=\"underline text-blue-400 hover:text-blue-300\" href=\"{create_pet_url}\">Add a pet</a> "
                        f"(or <a class=\"underline text-blue-400 hover:text-blue-300\" href=\"{wizard_url}\">use the wizard</a>)"
                    )
                )

            if suggestion_html_lines and not suggestion_shown:
                suggestion_html = "<br>".join(suggestion_html_lines)
                request.session["chat_suggestion_shown"] = True
        except Exception:
            pass

        bot_message = {"role": "bot", "text": bot_reply}
        if suggestion_html:
            bot_message["suggestion_html"] = suggestion_html
        history.append(bot_message)

        request.session["history"] = history
        request.session.modified = True
        return redirect("chat")
    
    # Personalized greeting (client shows this when no history exists)
    greeting = None
    if not history:
        if user_first and primary_pet:
            greeting = f"Hi {user_first}! I'm here to help you about {primary_pet.name}. Do you have any question?"
        elif user_first:
            greeting = f"Hi {user_first}! I'm here to help you with your dog or cat. Do you have any question?"
        else:
            greeting = None  # template will fallback to default text

    return render(request, "chat/chat.html", {
        "history": history,
        "user_first": user_first,
        "primary_pet": primary_pet,
        "greeting": greeting,
    })