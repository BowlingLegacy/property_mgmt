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
]
