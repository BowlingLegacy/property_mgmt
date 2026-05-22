from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import owner_views
from . import landlord_views
from . import auth_views as portal_auth_views
from . import blog_views

urlpatterns = [
    path("", views.home, name="home"),
    path("properties/", views.properties_list, name="properties_list"),
    path("creed/", views.creed, name="creed"),
    path("who-we-serve/", views.who_we_serve, name="who_we_serve"),
    path("property-owner-intake/", views.property_owner_intake, name="property_owner_intake"),
    path("property-owner-intake/success/", views.property_owner_intake_success, name="property_owner_intake_success"),

    path("apply/", views.apply, name="apply"),
    path("apply/success/", views.apply_success, name="apply_success"),
    path("enter-invite-code/", views.enter_invite_code, name="enter_invite_code"),
    path("request-invite-code/", views.request_invite_code, name="request_invite_code"),

    path("signup/", views.signup, name="signup"),
    path("login/", portal_auth_views.role_login, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="password_reset.html",
        email_template_name="password_reset_email.html",
        subject_template_name="password_reset_subject.txt",
        success_url="/password-reset/done/"
    ), name="password_reset"),

    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="password_reset_done.html"
    ), name="password_reset_done"),

    path("password-reset-confirm/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="password_reset_confirm.html",
        success_url="/password-reset/complete/"
    ), name="password_reset_confirm"),

    path("password-reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="password_reset_complete.html"
    ), name="password_reset_complete"),

    path("tenant-dashboard/", views.tenant_dashboard, name="tenant_dashboard"),
    path("tenant-dashboard/balance/", views.resident_balance_detail, name="resident_balance_detail"),
    path("tenant-dashboard/payment-history/", views.resident_payment_history, name="resident_payment_history"),
    path("tenant-dashboard/requests/", views.resident_requests, name="resident_requests"),
    path("tenant-dashboard/profile-photo/", views.update_resident_profile_photo, name="update_resident_profile_photo"),
    path("landlord-dashboard/", views.landlord_dashboard, name="landlord_dashboard"),
    path("landlord-dashboard/attention/", views.landlord_attention, name="landlord_attention"),
    path("landlord-dashboard/residents/", views.landlord_resident_files, name="landlord_resident_files"),
    path("owner-dashboard/", owner_views.property_owner_dashboard, name="property_owner_dashboard"),
    path("superadmin-dashboard/", views.superadmin_dashboard, name="superadmin_dashboard"),
    path("superadmin-dashboard/owners/", views.superadmin_owners, name="superadmin_owners"),
    path("superadmin-dashboard/owner-intakes/", views.superadmin_owner_intakes, name="superadmin_owner_intakes"),
    path("superadmin-dashboard/owner-intakes/<int:intake_id>/", views.superadmin_owner_intake_detail, name="superadmin_owner_intake_detail"),
    path("superadmin-dashboard/owner-intakes/<int:intake_id>/send-invite/", views.superadmin_send_owner_invite, name="superadmin_send_owner_invite"),
    path("superadmin-dashboard/residents/", views.superadmin_residents, name="superadmin_residents"),
    path("property-blogs/", blog_views.blog_manager, name="property_blog_manager"),
    path("property-blogs/create/", blog_views.blog_create, name="property_blog_create"),
    path("property-blogs/comments/<int:comment_id>/approve/", blog_views.approve_blog_comment, name="approve_blog_comment"),
    path("property-blogs/comments/<int:comment_id>/delete/", blog_views.delete_blog_comment, name="delete_blog_comment"),
    path("landlord/create-tenant/", landlord_views.create_tenant, name="landlord_create_tenant"),
    path("landlord-message/<int:message_id>/", views.landlord_message_detail, name="landlord_message_detail"),
    path("document/<int:document_id>/reviewed/", views.mark_document_reviewed, name="mark_document_reviewed"),

    path("payment-log/", views.payment_log, name="payment_log"),
    path("record-payment/", views.record_manual_payment, name="record_manual_payment"),
    path("payment/<int:payment_id>/receipt/", views.payment_receipt, name="payment_receipt"),
    path("rent-roll/", views.rent_roll, name="rent_roll"),
    path("t12-report/", views.t12_report, name="t12_report"),
    path("financial-upload/", views.financial_upload, name="financial_upload"),
    path("financial-upload/<int:upload_id>/parse/", views.parse_financial_upload, name="parse_financial_upload"),

    path("property-financials/<str:property_name>/", views.property_financials, name="property_financials"),

    path("export/payment-log/", views.export_payment_log_csv, name="export_payment_log_csv"),
    path("export/rent-roll/", views.export_rent_roll_csv, name="export_rent_roll_csv"),
    path("export/t12/", views.export_t12_csv, name="export_t12_csv"),

    path("property/<int:pk>/", views.property_detail, name="property_detail"),
    path("property/<int:pk>/existing-resident-profile/", views.existing_resident_intake, name="existing_resident_intake"),
    path("property/<int:pk>/existing-resident-profile/success/", views.existing_resident_intake_success, name="existing_resident_intake_success"),
    path("journal/<int:pk>/", views.blog_detail, name="blog_detail"),
    path("blog/<int:post_id>/comment/", views.add_blog_comment, name="add_blog_comment"),

    path("application/<int:pk>/view/", views.printable_application, name="application_detail"),
    path("application/<int:pk>/print/", views.printable_application, name="printable_application"),

    path("lease/sign/", views.lease_sign, name="lease_sign"),
    path("lease/submit/", views.submit_lease_signature, name="submit_lease_signature"),
    path("onboarding/document/<int:document_id>/", views.onboarding_document, name="onboarding_document"),
    path("onboarding/document/<int:document_id>/submit/", views.submit_onboarding_document, name="submit_onboarding_document"),

    path("pay/<int:application_id>/", views.create_checkout_session, name="pay_rent"),
    path("pay/<int:application_id>/<str:payment_type>/", views.create_checkout_session, name="pay_by_type"),

    path("payment-success/", views.payment_success, name="payment_success"),
    path("stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),

    path("resident-message/submit/", views.submit_resident_message, name="submit_resident_message"),
    path("resident-document/upload/", views.upload_resident_document, name="upload_resident_document"),
]
