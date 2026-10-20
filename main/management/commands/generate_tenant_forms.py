from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from django.core.management.base import BaseCommand
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib import colors
from main.resident_forms import (
    FORM_TYPES,
    PORTAL_GUIDANCE,
    NOTICE_GUIDANCE,
    PAYMENT_GUIDANCE,
    FEE_GUIDANCE,
)

STYLE = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14)


def paragraph(c, text, y):
    p = Paragraph(escape(text), STYLE)
    _, h = p.wrap(516, 720)
    p.drawOn(c, 48, y - h)
    return y - h - 14


def field(c, label, name, y, height=24):
    c.setFont("Helvetica", 10)
    c.drawString(48, y, label)
    c.acroForm.textfield(
        name=name,
        tooltip=label,
        x=48,
        y=y - height - 8,
        width=516,
        height=height,
        fontSize=10,
        borderColor=colors.HexColor("#64748b"),
        fillColor=colors.HexColor("#f8fafc"),
        fieldFlags="multiline" if height > 30 else "",
        maxlen=3000 if height > 30 else 160,
    )
    return y - height - 28


class Command(BaseCommand):
    help = "Generate blank fillable tenant request PDFs."

    def handle(self, *args, **options):
        directory = Path(settings.BASE_DIR) / "static/forms"
        for kind, (title, extra) in FORM_TYPES.items():
            c = canvas.Canvas(
                str(directory / ("tenant_" + kind + ".pdf")), pagesize=(612, 792)
            )
            c.setTitle(title)
            c.setAuthor("Bowling Legacy LLC")
            c.setFont("Helvetica-Bold", 19)
            c.drawString(48, 744, title)
            intro = "Complete and save this PDF. Attach it to a message from your tenant dashboard at bowlinglegacy.com. Keep your dated submission and review replies in My Requests."
            if kind == "move_out":
                intro += " I give written notice that I will terminate my month-to-month tenancy at the property and on the move-out date entered below. Check the notice period and delivery requirements for your tenancy."
            if kind == "maintenance":
                intro += (
                    " For emergencies, call emergency services and management directly."
                )
            if kind == "late_payment":
                intro += " Enter the same rent month and payment date in the dashboard. Only written landlord approval pauses assessment; a request alone does not."
            if kind == "accommodation":
                intro += " Describe the accommodation needed; avoid unnecessary medical details."
            y = paragraph(c, intro, 715)
            for name, label in [
                ("resident_name", "Tenant full legal name"),
                ("property_room", "Property address and room / unit"),
                ("landlord", "Landlord / authorized recipient"),
                ("contact", "Tenant phone / email"),
            ] + extra:
                y = field(
                    c, label, name, y, 54 if name in ("details", "request") else 24
                )
            y = field(c, "Tenant signature / typed name", "signature", y)
            y = field(c, "Date signed (YYYY-MM-DD)", "signed_date", y)
            note = (
                NOTICE_GUIDANCE
                if kind in ("move_out", "notice")
                else "This submission is filed for landlord review. It does not change rent due dates, authorize entry, establish emergency response or create an approved agreement by itself."
            )
            # Put legal delivery instructions on a separate page with ample room.
            c.setFont("Helvetica", 9)
            c.drawString(
                48, 26, "Bowling Legacy LLC | Tenant dashboard form | Page 1 of 2"
            )
            c.showPage()
            c.setFont("Helvetica-Bold", 17)
            c.drawString(48, 744, "Submission and delivery instructions")
            y = paragraph(c, PORTAL_GUIDANCE, 711)
            y = paragraph(c, note, y)
            if kind == "late_payment":
                y = paragraph(c, FEE_GUIDANCE, y)
            y = paragraph(
                c,
                "Landlord mailing address and formal-notice contact: use the details in your signed lease or supplied notice information. Request a copy from management if needed. Keep proof of any separate lawful delivery.",
                y,
            )
            c.setFont("Helvetica", 9)
            c.drawString(
                48, 26, "Bowling Legacy LLC | Tenant dashboard form | Page 2 of 2"
            )
            c.save()
            self.stdout.write(title)
