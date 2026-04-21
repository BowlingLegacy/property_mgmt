from django.urls import path
from . import views

urlpatterns = [
    path('', views.property_list, name='home'),
    path('properties/', views.property_list, name='property_list'),
    path('properties/<slug:slug>/', views.property_detail, name='property_detail'),
    path('properties/<slug:slug>/apply/', views.apply_for_property, name='apply_for_property'),
    path('application-submitted/', views.application_submitted, name='application_submitted'),

    path('owner/dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/documents/', views.manage_owner_documents, name='manage_owner_documents'),
    path('owner/properties/<int:property_id>/photos/', views.manage_property_photos, name='manage_property_photos'),
    path('owner/applications/<int:application_id>/background-check/', views.run_background_check, name='run_background_check'),
]
