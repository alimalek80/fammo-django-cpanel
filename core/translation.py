from modeltranslation.translator import register, TranslationOptions
from .models import HeroSection, FAQ

@register(HeroSection)
class HeroSectionTranslationOptions(TranslationOptions):
    fields = ('heading', 'subheading', 'subheading_secondary',)

@register(FAQ)
class FAQTranslationOptions(TranslationOptions):
    fields = ('question', 'answer',)