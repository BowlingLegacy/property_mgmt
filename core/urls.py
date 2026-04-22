from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # All main app URLs (homepage, uploader, selector)
    path("", include("main.urls")),
]

# Serve media files (uploaded images)
# Required for both DEBUG and production on Render
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
