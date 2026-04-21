from django.urls import path
from . import views

urlpatterns = [
    path('', views.property_list, name='home'),
    path('properties/', views.property_list, name='property_list'),
    path('properties/<slug:slug>/', views.property_detail, name='property_detail'),
    path('properties/<slug:slug>/apply/', views.apply_for_property, name='apply_for_property'),
    path('application-submitted/', views.application_submitted, name='application_submitted'),
    path('signup/', views.signup, name='signup'),
]

