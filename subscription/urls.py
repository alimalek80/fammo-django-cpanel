from django.urls import path
from .views import subscription_plans_view

urlpatterns = [
    path('plans/', subscription_plans_view, name='subscription_plans'),
]
