from django import template

register = template.Library()

@register.filter
def pet_age(pet):
    """Display pet's current age calculated from birth_date"""
    if pet:
        return pet.get_age_display()
    return ""

@register.simple_tag
def pet_age_years(pet):
    """Get pet's current age in years"""
    if pet:
        age = pet.get_current_age()
        return age['years']
    return 0

@register.simple_tag
def pet_age_months(pet):
    """Get pet's current age in months"""
    if pet:
        age = pet.get_current_age()
        return age['months']
    return 0

@register.simple_tag
def pet_age_weeks(pet):
    """Get pet's current age in weeks"""
    if pet:
        age = pet.get_current_age()
        return age['weeks']
    return 0
