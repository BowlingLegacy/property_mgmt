from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.http import Http404
from django.views.static import serve


def serve_public_media(request, path):
    public_prefixes = ("property_photos/", "property_gallery/", "blog_images/")
    normalized_path = path.replace("\\", "/").lstrip("/")
    if ".." in normalized_path.split("/") or not normalized_path.startswith(public_prefixes):
        raise Http404
    return serve(request, normalized_path, document_root=settings.MEDIA_ROOT)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("main.urls")),
]

# Only intentionally public imagery is available without authorization.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve_public_media),
]
