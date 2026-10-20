"""Private staff templates; completed copies belong in the selected resident file."""

from pathlib import Path
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import ApplicantDocument, HousingApplication, ResidentMessage
from .resident_forms import validate_submission

DOCUMENTS = {
    "inspection": dict(
        title="Fillable move-in / move-out inspection report",
        file="rental_inspection_fillable.pdf",
        category="Ready to use",
        note="Six-page report with editable property details, condition tables, repairs, signatures and deductions. Save the completed PDF before filing it below.",
        usable=True,
    ),
    "receipt": dict(
        title="Fillable rent receipt",
        file="rent_receipt_fillable.pdf",
        category="Ready to use",
        note="Enter the correct property and payment details. Rent and any existing late fees remain separate. Filing a receipt does not post a payment or change the ledger.",
        usable=True,
    ),
    "inspection_guidance": dict(
        title="Inspection tips and supporting guidance",
        file="originals/inspection_guidance.pdf",
        category="Reference",
        note="The same two guidance pages appear at the front of the original inspection report. Kept separately for staff reference.",
        usable=False,
    ),
    "inspection_original": dict(
        title="Original Belmont inspection report",
        file="originals/inspection_original.pdf",
        category="Original reference",
        note="Original eight-page upload, unchanged. The six-page fillable version above has editable property details.",
        usable=False,
    ),
    "receipt_original": dict(
        title="Original rent receipt",
        file="originals/receipt_original.pdf",
        category="Original reference",
        note="Reference only: fixed Medford address and late-fee wording conflict with the current lease forms. Use the corrected fillable receipt above.",
        usable=False,
    ),
    "violation_one": dict(
        title="Lease-violation notice - one tenant",
        file="originals/lease_violation_one_tenant.pdf",
        category="Needs review before use",
        note="Original preserved. Not a ready-to-serve notice: contains a fixed October 19, 2026 move-out date and a generic cure period. The correct notice, grounds, dates and delivery must be determined for the actual case. This is not a court eviction order.",
        usable=False,
    ),
    "violation_two": dict(
        title="Lease-violation notice - two tenants",
        file="originals/lease_violation_two_tenants.pdf",
        category="Needs review before use",
        note="Original preserved. Not a ready-to-serve notice: contains a fixed October 19, 2026 move-out date and an unspecified cure period. The correct notice, grounds, dates and delivery must be determined for the actual case. This is not a court eviction order.",
        usable=False,
    ),
}


def require_staff(user):
    from .views import reporting_required

    if not reporting_required(user):
        raise PermissionDenied


@login_required
def document_library(request):
    require_staff(request.user)
    from .views import staff_managed_applications

    residents = (
        staff_managed_applications(request.user)
        .select_related("property")
        .order_by("property__name", "full_name")
    )
    if request.method == "POST":
        try:
            resident_id = int(request.POST.get("resident") or 0)
        except ValueError:
            raise Http404
        resident = get_object_or_404(residents, pk=resident_id)
        kind = request.POST.get("document_kind")
        entry = DOCUMENTS.get(kind)
        try:
            if not entry or not entry["usable"]:
                raise ValidationError(
                    "Choose a ready-to-use inspection or receipt form."
                )
            upload, _, _ = validate_submission(request, "document")
            if not upload:
                raise ValidationError("Attach the completed PDF before filing it.")
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            with transaction.atomic():
                document = ApplicantDocument.objects.create(
                    application=resident,
                    document_type="other",
                    file=upload,
                    name=entry["title"],
                    locked=True,
                    status="locked",
                    submitted_at=timezone.now(),
                )
                ResidentMessage.objects.create(
                    application=resident,
                    message_type="document",
                    subject=entry["title"],
                    message=request.POST.get("message", "").strip()
                    or "A completed document has been filed. Open the attached PDF and contact management through My Requests with any questions.",
                    attachment=document,
                    status="reviewed",
                    locked=True,
                )
            messages.success(
                request,
                "Completed PDF filed in the resident record and inbox. No payment or charge was posted.",
            )
            return redirect("document_library")
    return render(
        request,
        "document_library.html",
        dict(
            documents=[dict(key=k, **v) for k, v in DOCUMENTS.items()],
            residents=residents,
        ),
    )


@login_required
def library_download(request, key):
    require_staff(request.user)
    entry = DOCUMENTS.get(key)
    if not entry:
        raise Http404
    path = Path(settings.BASE_DIR) / "private_forms" / entry["file"]
    return FileResponse(
        path.open("rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename=path.name,
    )
