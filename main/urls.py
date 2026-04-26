from django.urls import path
from main import views

urlpatterns = [
    # Public pages
    path("", views.home, name="home"),
    path("creed/", views.creed, name="creed"),

    # Application flow
    path("apply/", views.apply, name="apply"),
    path("apply/success/", views.apply_success, name="apply_success"),
    path("enter-invite-code/", views.enter_invite_code, name="enter_invite_code"),

    # Landlord dashboard
    path("landlord-dashboard/", views.landlord_dashboard, name="landlord_dashboard"),

    # Property detail
    path("property/<int:pk>/", views.property_detail, name="property_detail"),
]
