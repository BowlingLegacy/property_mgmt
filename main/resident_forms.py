"""Tenant PDFs and validation for documents delivered to the private inbox."""

from datetime import date
from io import BytesIO
from pathlib import Path
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError
from pypdf import PdfReader

FORM_TYPES = {
    "maintenance": (
        "Maintenance Request",
        [
            ("location", "Repair location / room"),
            ("details", "Problem, when it started and urgency"),
            ("access", "Contact and access arrangements"),
        ],
    ),
    "move_out": (
        "30-Day Move-Out Notice",
        [
            ("move_out_date", "Intended termination / move-out date"),
            ("forwarding_address", "Forwarding address"),
            ("service_details", "Delivery method, date and recipient"),
        ],
    ),
    "late_payment": (
        "Late Payment Arrangement Request",
        [
            ("rent_month", "Rent month (YYYY-MM)"),
            ("payment_date", "Promised payment date (YYYY-MM-DD)"),
            ("amount", "Amount and proposed payment method"),
        ],
    ),
    "accommodation": (
        "Accommodation Request",
        [
            ("request", "Accommodation requested"),
            ("timing", "Requested timing"),
            ("followup_contact", "Preferred private follow-up contact"),
        ],
    ),
    "notice": (
        "Other Written Notice",
        [
            ("purpose", "Notice purpose"),
            ("details", "Details and requested response"),
            ("service_details", "Delivery method, date and recipient"),
        ],
    ),
}
PORTAL_GUIDANCE = "The tenant dashboard at bowlinglegacy.com is the most effective way to reach management for maintenance, notices, documents and payment arrangements. Download a fillable PDF, save it, then attach it to a dashboard message. A dated copy is filed in your resident record and landlord inbox."
NOTICE_GUIDANCE = "Dashboard submission records your communication; it does not by itself establish legal service. For a month-to-month move-out, generally give at least 30 days' written notice under ORS 90.427 and deliver it under ORS 90.155. First-class mail generally adds three days. Email service requires a qualifying written addendum; termination by email also requires first-class mail. Follow the notice rules applicable to your tenancy."
PAYMENT_GUIDANCE = "Pay rent through bowlinglegacy.com, Cash App $Trmf8763 (cash.app/$Trmf8763), or your bank's online bill pay to our business account. Request verified business payee/account instructions privately through the tenant dashboard before setting up bank bill pay. Include your name, room and rent month. Schedule payment early enough to be received by the deadline."
FEE_GUIDANCE = "An agreed late fee is added automatically to the balance on the day after the applicable legal and lease pay-by period expires, only under a valid written late-fee policy. Fees stay separate from rent. Painted Lady: rent due on the 1st, pay by 11:59 p.m. Pacific on the 5th, one $25 fee on the 6th. Belmont: pay by 11:59 p.m. Pacific on the 8th, one agreed 5% fee on the 9th, only if lawful and reasonable. Contact the landlord through the dashboard before the deadline, state when rent will be paid, and obtain written approval to avoid the fee. A request alone does not pause a fee. An approved arrangement pauses assessment through the approved payment date; if rent is not received by then, the agreed fee may be assessed the following day."


@login_required
def tenant_form(request, kind):
    if kind not in FORM_TYPES or not getattr(request.user, "resident_profile", None):
        raise Http404
    path = Path(settings.BASE_DIR) / "static" / "forms" / ("tenant_" + kind + ".pdf")
    return FileResponse(
        path.open("rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename=path.name,
    )


def validate_submission(request, message_type):
    from .models import ResidentMessage

    if message_type not in dict(ResidentMessage.MESSAGE_TYPE_CHOICES):
        raise ValidationError("Choose a valid message type.")
    upload = request.FILES.get("attachment")
    if message_type in {"move_out", "late_payment", "notice"} and not upload:
        raise ValidationError("Attach your saved PDF form for this request.")
    if upload:
        if upload.size > 5 * 1024 * 1024 or not upload.name.lower().endswith(".pdf"):
            raise ValidationError("Attach a PDF no larger than 5 MB.")
        try:
            data = upload.read()
            if not data.startswith(b"%PDF-"):
                raise ValueError
            pdf = PdfReader(BytesIO(data), strict=True)
            if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 20:
                raise ValueError
            # Reject active content in documents shown inside the private portal.
            for obj in pdf.xref.values():
                for number in obj:
                    from pypdf.generic import IndirectObject

                    value = pdf.get_object(IndirectObject(number, 0, pdf))
                    if isinstance(value, dict) and any(
                        key in value
                        for key in (
                            "/JS",
                            "/JavaScript",
                            "/Launch",
                            "/OpenAction",
                            "/AA",
                            "/EmbeddedFiles",
                        )
                    ):
                        raise ValueError
        except Exception:
            raise ValidationError(
                "Use a readable, unencrypted PDF without scripts or embedded files (maximum 20 pages)."
            )
        finally:
            upload.seek(0)
    month = promised = None
    if message_type == "late_payment":
        try:
            month = date.fromisoformat(request.POST.get("service_month", "") + "-01")
            promised = date.fromisoformat(request.POST.get("promised_payment_date", ""))
            from django.utils import timezone
            from .late_fees import PACIFIC

            if (
                promised < timezone.localtime(timezone.now(), PACIFIC).date()
                or promised < month
            ):
                raise ValueError
        except ValueError:
            raise ValidationError(
                "Enter the rent month and a valid promised payment date today or later."
            )
    return upload, month, promised
