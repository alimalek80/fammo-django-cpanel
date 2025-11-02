from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language
from django.urls import path, include
from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ✅ This is required for {% url 'set_language' %} to work
    path('i18n/', include('django.conf.urls.i18n')),
    path('markdownx/', include('markdownx.urls')),
]

# Your actual app routes
urlpatterns += i18n_patterns(
    path('', include(('core.urls', 'core'), namespace='core')),
    path('users/', include('userapp.urls')),
    path('pets/', include(('pet.urls', 'pet'), namespace='pet')),
    path('admin/', admin.site.urls),
    path('ai/', include('aihub.urls')),
    path('subscription/', include('subscription.urls')),
    path('blog/', include('blog.urls')),
    path('chat/', include('chat.urls')),
)

urlpatterns += [
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='userapp/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='userapp/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='userapp/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='userapp/password_reset_complete.html'), name='password_reset_complete'),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    # Include django_browser_reload URLs only in DEBUG mode
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
