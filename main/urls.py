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
    path("logout/", views.logout_view, name="logout"),

    path("password-reset/", auth_views.PasswordResetView.as_view(
    template_name="password_reset.html",
    email_template_name="password_reset_email.html",
    subject_template_name="password_reset_subject.txt",
    success_url="/password-reset/done/"
),  name="password_reset"),

    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
    template_name="password_reset_done.html"
),  name="password_reset_done"),

    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
    template_name="password_reset_confirm.html",
    success_url="/password-reset/complete/"
),  name="password_reset_confirm"),

    path("password-reset/complete/", auth_views.PasswordResetCompleteView.as_view(
    template_name="password_reset_complete.html"
),  name="password_reset_complete"),
    

    path("tenant-dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("landlord-dashboard/", views.landlord_dashboard, name="landlord_dashboard"),
    path("landlord-message/<int:message_id>/", views.landlord_message_detail, name="landlord_message_detail"),

    path("payment-log/", views.payment_log, name="payment_log"),
    path("rent-roll/", views.rent_roll, name="rent_roll"),
    path("t12-report/", views.t12_report, name="t12_report"),
    path("financial-upload/", views.financial_upload, name="financial_upload"),
    path("financial-upload/<int:upload_id>/parse/", views.parse_financial_upload, name="parse_financial_upload"),

    path("property-financials/<str:property_name>/", views.property_financials, name="property_financials"),

    path("export/payment-log/", views.export_payment_log_csv, name="export_payment_log_csv"),
    path("export/rent-roll/", views.export_rent_roll_csv, name="export_rent_roll_csv"),
    path("export/t12/", views.export_t12_csv, name="export_t12_csv"),

    path("property/<int:pk>/", views.property_detail, name="property_detail"),
    path("journal/<int:pk>/", views.blog_detail, name="blog_detail"),
    path("blog/<int:post_id>/comment/", views.add_blog_comment, name="add_blog_comment"),

    path("application/<int:pk>/print/", views.printable_application, name="printable_application"),

    path("lease/sign/", views.lease_sign, name="lease_sign"),
    path("lease/submit/", views.submit_lease_signature, name="submit_lease_signature"),
    
    path("pay/<int:application_id>/", views.create_checkout_session, name="pay_rent"),
    path("pay/<int:application_id>/<str:payment_type>/", views.create_checkout_session, name="pay_by_type"),

    path("payment-success/", views.payment_success, name="payment_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),

    path("resident-message/submit/", views.submit_resident_message, name="submit_resident_message"),
    path("resident-document/upload/", views.upload_resident_document, name="upload_resident_document"),
]
