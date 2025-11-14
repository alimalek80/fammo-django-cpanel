from django.urls import path
from . import views
from .views import AIHistoryView

urlpatterns = [
    path('recommend/<int:pet_id>/', views.generate_meal_recommendation, name='generate_meal'),
    path('health-report/<int:pet_id>/', views.generate_health_report, name='generate_health'),
    path('history/', AIHistoryView.as_view(), name='ai_history'),
]
