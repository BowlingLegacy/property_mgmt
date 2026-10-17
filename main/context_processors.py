from urllib.parse import urlparse

from django.conf import settings
from django.urls import NoReverseMatch, Resolver404, resolve, reverse
from django.utils.http import url_has_allowed_host_and_scheme


DASHBOARD_ROUTES = {
    "superadmin_dashboard": "Super Admin Dashboard",
    "property_owner_dashboard": "Owner Dashboard",
    "landlord_dashboard": "Landlord Dashboard",
    "tenant_dashboard": "Resident Dashboard",
}


def _default_dashboard_route(user):
    if user.is_superuser or getattr(user, "role", "") == "admin":
        return "superadmin_dashboard"
    if getattr(user, "role", "") == "property_owner":
        return "property_owner_dashboard"
    if user.is_staff or getattr(user, "role", "") in {"landlord", "assistant"}:
        return "landlord_dashboard"
    return "tenant_dashboard"


def dashboard_return_navigation(request):
    """Provide one safe return destination for every authenticated portal page."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"show_dashboard_return": False}

    current_route = getattr(getattr(request, "resolver_match", None), "url_name", None)
    if current_route in DASHBOARD_ROUTES:
        request.session["dashboard_return_route"] = current_route
        request.session["dashboard_return_url"] = request.get_full_path()
        return {"show_dashboard_return": False}

    route_name = None
    return_url = None
    referrer = request.META.get("HTTP_REFERER", "")
    if url_has_allowed_host_and_scheme(referrer, allowed_hosts={request.get_host()}):
        referrer_url = urlparse(referrer)
        try:
            referrer_route = resolve(referrer_url.path).url_name
        except Resolver404:
            referrer_route = None
        if referrer_route in DASHBOARD_ROUTES:
            route_name = referrer_route
            return_url = referrer_url.path
            if referrer_url.query:
                return_url += f"?{referrer_url.query}"
            request.session["dashboard_return_route"] = route_name
            request.session["dashboard_return_url"] = return_url

    if route_name is None:
        route_name = request.session.get("dashboard_return_route")
        return_url = request.session.get("dashboard_return_url")
    if route_name not in DASHBOARD_ROUTES or not isinstance(return_url, str) or not return_url.startswith("/"):
        route_name = _default_dashboard_route(user)
        try:
            return_url = reverse(route_name)
        except NoReverseMatch:
            return {"show_dashboard_return": False}

    return {
        "show_dashboard_return": True,
        "dashboard_return_url": return_url,
        "dashboard_return_label": DASHBOARD_ROUTES[route_name],
        "dashboard_route_urls": [reverse(name) for name in DASHBOARD_ROUTES],
    }


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
