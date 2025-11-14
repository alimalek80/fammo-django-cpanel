from django.urls import path
from . import views

urlpatterns = [
    path('', views.blog_list, name='blog_list'),
    path('<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('<slug:slug>/rate/', views.rate_post, name='rate_post'),
    path('<slug:slug>/comment/', views.comment_post, name='comment_post'),
]