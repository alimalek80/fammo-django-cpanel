from core.models import SocialLinks

def social_links(request):
    links = SocialLinks.objects.first()
    return {'social_links': links}