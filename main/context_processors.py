from urllib.parse import urlparse

from django.conf import settings


def demo_mode(request):
    request_host = request.get_host().split(":")[0].lower() if request else ""
    demo_public_host = urlparse(getattr(settings, "DEMO_PUBLIC_URL", "")).netloc.split(":")[0].lower()
    settings_demo_mode = getattr(settings, "DEMO_MODE", False)
    host_looks_like_demo = "demo" in request_host or (demo_public_host and request_host == demo_public_host)
    show_demo_mode = settings_demo_mode and host_looks_like_demo

    return {
        "demo_mode": show_demo_mode,
        "demo_session_seconds": getattr(settings, "DEMO_SESSION_SECONDS", 7200),
        "demo_public_url": getattr(settings, "DEMO_PUBLIC_URL", ""),
    }
