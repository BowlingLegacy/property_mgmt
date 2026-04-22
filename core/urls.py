from django.contrib import admin
from django.urls import path
from main import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Homepage
    path("", views.homepage_view, name="homepage"),

    # Homepage image admin tools
    path("admin-upload-homepage-image/", views.upload_homepage_image, name="upload_homepage_image"),
    path("admin-select-homepage-image/", views.select_homepage_image, name="select_homepage_image"),
]

# Serve media files (uploaded images)
# This MUST be at the bottom
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Render production also needs this because Whitenoise does NOT serve media
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
