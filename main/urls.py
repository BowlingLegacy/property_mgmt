from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("creed/", views.creed, name="creed"),

    path("apply/", views.apply, name="apply"),
    path("apply/success/", views.apply_success, name="apply_success"),
    path("enter-invite-code/", views.enter_invite_code, name="enter_invite_code"),

    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="home"), name="logout"),

    path("tenant-dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("landlord-dashboard/", views.landlord_dashboard, name="landlord_dashboard"),
    path("payment-log/", views.payment_log, name="payment_log"),

    path("property/<int:pk>/", views.property_detail, name="property_detail"),
    path("journal/<int:pk>/", views.blog_detail, name="blog_detail"),

    path("application/<int:pk>/print/", views.printable_application, name="printable_application"),

    path("blog/<int:post_id>/comment/", views.add_blog_comment, name="add_blog_comment"),

    path("pay/<int:application_id>/", views.create_checkout_session, name="pay_rent"),
    path("pay/<int:application_id>/<str:payment_type>/", views.create_checkout_session, name="pay_by_type"),

    path("payment-success/", views.payment_success, name="payment_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
]
