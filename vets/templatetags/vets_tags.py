from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Split a string by the given argument"""
    if value:
        return value.split(arg)
    return []

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary"""
    return dictionary.get(key)

@register.simple_tag
def clinic_referral_url(request, clinic):
    """Generate a referral URL for a clinic"""
    if clinic and clinic.active_referral_code:
        from django.urls import reverse
        referral_path = reverse('vets:referral_landing', kwargs={'code': clinic.active_referral_code})
        return request.build_absolute_uri(referral_path)
    return ''

@register.filter
def strip(value):
    """Strip whitespace from a string"""
    if value:
        return str(value).strip()
    return value

@register.filter
def mul(value, arg):
    """Multiply two values"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide two values"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.inclusion_tag('vets/partials/clinic_card.html')
def clinic_card(clinic, show_referral=False):
    """Render a clinic card"""
    return {
        'clinic': clinic,
        'show_referral': show_referral,
    }