from django.urls import path
from . import views

urlpatterns = [
    path("", views.temp_home, name="home"),

    # Admin-only drag-and-drop uploader
    path("admin-upload-homepage-image/", views.admin_upload_homepage_image, name="admin_upload_homepage_image"),

    # Admin selects which image is active
    path("admin-select-homepage-image/", views.admin_select_homepage_image, name="admin_select_homepage_image"),

    # Future owner uploader (not used yet)
    path("owner-upload-image/", views.owner_upload_image, name="owner_upload_image"),
]
