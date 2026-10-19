from pathlib import Path
from xml.sax.saxutils import escape
from django.conf import settings
from django.core.management.base import BaseCommand
from reportlab.pdfgen import canvas
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Paragraph
from main.lease_terms import lease_sections, INITIALS


class LeasePDF:
    def __init__(self, path):
        self.pdf = canvas.Canvas(str(path), pagesize=(612, 792))
        self.pdf.setTitle("The Painted Lady Inn - Fillable Residential Lease Agreement")
        self.pdf.setAuthor("Bowling Legacy LLC")
        self.page = 1
        self.y = 741
        self.fields = []
        self.body_style = ParagraphStyle(
            "lease", fontName="Times-Roman", fontSize=12, leading=18
        )

    def footer(self):
        self.pdf.setFont("Times-Roman", 10)
        self.pdf.drawRightString(574, 20, f"Page {self.page}")

    def new_page(self):
        self.footer()
        self.pdf.showPage()
        self.page += 1
        self.y = 732
        self.pdf.setFont("Times-Roman", 10)
        self.pdf.drawString(
            38, 760, "The Painted Lady Inn - Residential Lease Agreement"
        )

    def heading(self, text, first_paragraph=None):
        p = Paragraph(
            escape(text),
            ParagraphStyle(
                "heading", fontName="Helvetica-Bold", fontSize=12, leading=17
            ),
        )
        _, h = p.wrap(507, 700)
        first_height = 0
        if first_paragraph:
            first_height = Paragraph(escape(first_paragraph), self.body_style).wrap(
                474.5, 700
            )[1]
        if self.y - h - 14 - first_height < 55:
            self.new_page()
        p.drawOn(self.pdf, 67.5, self.y - h)
        self.y -= h + 14

    def paragraph(self, text):
        p = Paragraph(escape(text), self.body_style)
        _, h = p.wrap(474.5, 700)
        if self.y - h < 55:
            self.new_page()
        p.drawOn(self.pdf, 99.75, self.y - h)
        self.y -= h + 13

    def field(self, label, name, width=528, height=20, multiline=False):
        if self.y - height < 75:
            self.new_page()
        self.pdf.setFont("Times-Roman", 12)
        self.pdf.drawString(42, self.y, label)
        self.y -= height + 6
        self.pdf.acroForm.textfield(
            name=name,
            tooltip=label,
            x=42,
            y=self.y,
            width=width,
            height=height,
            borderWidth=0.5,
            borderStyle="solid",
            forceBorder=True,
            fontName="Times-Roman",
            fontSize=0,
            fieldFlags=4096 if multiline else 0,
            maxlen=0,
            fillColor=colors.white,
            textColor=colors.black,
            borderColor=colors.HexColor("#555555"),
        )
        self.fields.append(name)
        self.y -= 18

    def write(self):
        self.pdf.setFont("Times-Bold", 14)
        self.pdf.drawCentredString(306, 742, "RESIDENTIAL LEASE AGREEMENT")
        self.pdf.setFont("Times-Roman", 12)
        self.pdf.drawCentredString(
            306, 717, "The Painted Lady Inn - Month-to-Month Room Tenancy"
        )
        self.y = 682
        for label, name in [
            ("Landlord / authorized representative", "landlord_name"),
            ("Resident full legal name", "resident_name"),
            ("Property street address", "property_address"),
            ("Assigned room / space", "room_space"),
            ("Tenancy start date", "lease_start_date"),
            ("Monthly rent ($)", "monthly_rent"),
            ("Monthly shared utility contribution ($)", "utility_fee"),
            ("Security deposit ($)", "security_deposit"),
            (
                "Deposit plan (paid in full, or approved three installments within 90 days)",
                "deposit_payment_plan",
            ),
            (
                "Landlord / agent physical mailing address for notices",
                "landlord_notice_address",
            ),
            ("Landlord / agent phone and email", "landlord_contact"),
        ]:
            self.field(label, name)
        self.pdf.setFont("Times-Roman", 11)
        self.pdf.drawString(
            42,
            self.y,
            "Rent due: 1st. Collection: 3rd. Pay by end of 5th; one $25 late fee on 6th.",
        )
        self.new_page()
        for section in lease_sections():
            self.heading(
                f"{section['number']}. {section['title']}", section["paragraphs"][0]
            )
            for p in section["paragraphs"]:
                self.paragraph(p)
        self.new_page()
        self.heading("Resident Initials and Execution")
        self.paragraph(
            "Read all terms and complete the lease particulars before signing. Required disclosures and lawful written house rules must be supplied and identified. An updated agreement does not retroactively change an existing signed lease or waive legally required notice."
        )
        for name, label in INITIALS:
            self.field("Initials - " + label, name, width=100)
        for label, name in [
            ("Resident printed legal name", "resident_printed_name"),
            ("Resident signature", "resident_signature"),
            ("Resident signing date", "resident_signature_date"),
            (
                "Landlord / authorized representative printed name",
                "landlord_printed_name",
            ),
            ("Landlord / authorized representative signature", "landlord_signature"),
            ("Landlord signing date", "landlord_signature_date"),
        ]:
            self.field(label, name)
        self.footer()
        self.pdf.save()
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject

        reader = PdfReader(self.pdf._filename)
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        for page in writer.pages:
            for ref in page.get("/Annots", []):
                field = ref.get_object()
                field.pop(NameObject("/MaxLen"), None)
        with open(self.pdf._filename, "wb") as stream:
            writer.write(stream)
        return {"pages": self.page, "fields": len(self.fields)}


class Command(BaseCommand):
    help = "Create the plain, fillable Painted Lady lease using the same terms as the resident portal."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path)

    def handle(self, *args, **options):
        output = (
            options["output"]
            or settings.BASE_DIR / "static/forms/painted_lady_residential_lease.pdf"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        result = LeasePDF(output).write()
        self.stdout.write(
            f"Created {output}: {result['pages']} pages; {result['fields']} fillable fields."
        )
