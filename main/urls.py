from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Homepage
    path("", views.home, name="home"),

    # Authentication
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),
    path("signup/", views.signup, name="signup"),

    # Portals
    path("tenant/dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("landlord/dashboard/", views.landlord_dashboard, name="landlord_dashboard"),

    # Property Detail Page
    path("property/<int:pk>/", views.property_detail, name="property_detail"),

    # ----------------------------------------------------
    # PHASE 3 — INVITE CODE APPLICATION SYSTEM
    # ----------------------------------------------------

    # Step 1: Enter Invite Code
    path("apply/", views.enter_invite_code, name="enter_invite_code"),

    # Step 2: Application Form (landlord-specific)
    path("apply/<int:landlord_id>/", views.apply, name="apply"),

    # Step 3: Application Success Page
    path("application-success/", views.application_success, name="application_success"),
]
