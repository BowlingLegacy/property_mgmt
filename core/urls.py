from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Route ALL main app URLs through main/urls.py
    path("", include("main.urls")),
]

# Serve media files (uploaded images)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

