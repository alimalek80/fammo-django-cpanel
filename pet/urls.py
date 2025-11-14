from django.urls import path
from . import views
from .views import export_pets_csv, PetWizard, FORMS

urlpatterns = [
    path('create/', views.pet_form_view, name='create_pet'),
    path('wizard/', PetWizard.as_view(FORMS), name='pet_wizard'),
    path('edit/<int:pk>/', views.pet_form_view, name='edit_pet'),
    path('my-pets/', views.my_pets_view, name='my_pets'),
    path('delete/<int:pk>/', views.delete_pet_view, name='delete_pet'),
    path('ajax/load-breeds/', views.load_breeds, name='ajax_load_breeds'),
    path('detail/<int:pk>/', views.pet_detail_view, name='pet_detail'),
    path('export/pets/', export_pets_csv, name='export_pets_csv'),
]