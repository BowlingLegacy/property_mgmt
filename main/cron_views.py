import json, secrets
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .late_fees import assess_late_fees


@csrf_exempt
@require_POST
def assess_late_fees_job(request):
    token = getattr(settings, "LATE_FEE_JOB_TOKEN", "")
    if not token or not secrets.compare_digest(
        request.headers.get("Authorization", ""), f"Bearer {token}"
    ):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    try:
        payload = json.loads(request.body or b"{}")
        if (
            not isinstance(payload, dict)
            or set(payload) - {"dry_run"}
            or not isinstance(payload.get("dry_run", False), bool)
        ):
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid job request"}, status=400)
    return JsonResponse(assess_late_fees(dry_run=payload.get("dry_run", False)))
