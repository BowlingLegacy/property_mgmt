class PropertyWorkspaceScopeMiddleware:
    """Attach the explicitly selected property workspace to the authenticated user."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, "user", None) and request.user.is_authenticated:
            property_id = request.session.get("active_property_workspace_id")
            if property_id:
                request.user._active_property_workspace_id = property_id
        return self.get_response(request)
