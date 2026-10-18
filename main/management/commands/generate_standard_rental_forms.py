from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


GOLD = HexColor("#C59A32")
INK = HexColor("#111111")
PAPER = HexColor("#FFFAF0")


class FillableForm:
    def __init__(self, path, title, subtitle):
        self.path = path
        self.title = title
        self.subtitle = subtitle
        self.pdf = canvas.Canvas(str(path), pagesize=letter)
        self.form = self.pdf.acroForm
        self.page = 0
        self.y = 0
        self.new_page()

    def new_page(self):
        if self.page:
            self.footer()
            self.pdf.showPage()
        self.page += 1
        self.pdf.setFillColor(PAPER)
        self.pdf.rect(0, 0, 612, 792, fill=1, stroke=0)
        self.pdf.setFillColor(INK)
        self.pdf.setFont("Helvetica-Bold", 17)
        self.pdf.drawString(42, 750, self.title)
        self.pdf.setFillColor(GOLD)
        self.pdf.rect(42, 735, 528, 3, fill=1, stroke=0)
        self.pdf.setFillColor(INK)
        self.pdf.setFont("Helvetica", 8.5)
        self.pdf.drawString(42, 720, self.subtitle)
        self.y = 690

    def footer(self):
        self.pdf.setFont("Helvetica", 7)
        self.pdf.setFillColor(HexColor("#555555"))
        self.pdf.drawString(42, 25, "RentalReadyPro reusable form - property-specific terms and current law control.")
        self.pdf.drawRightString(570, 25, f"Page {self.page}")

    def section(self, text):
        if self.y < 150:
            self.new_page()
        self.pdf.setFillColor(INK)
        self.pdf.rect(42, self.y - 3, 528, 20, fill=1, stroke=0)
        self.pdf.setFillColor(PAPER)
        self.pdf.setFont("Helvetica-Bold", 10)
        self.pdf.drawString(50, self.y + 3, text.upper())
        self.pdf.setFillColor(INK)
        self.y -= 32

    def note(self, text, height=28):
        if self.y - height < 55:
            self.new_page()
        words = text.split()
        line = ""
        lines = []
        for word in words:
            candidate = f"{line} {word}".strip()
            if self.pdf.stringWidth(candidate, "Helvetica", 8) > 520:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        self.pdf.setFont("Helvetica", 8)
        for item in lines:
            self.pdf.drawString(45, self.y, item)
            self.y -= 11
        self.y -= 5

    def field(self, label, name, width=528, height=18, multiline=False):
        needed = height + 24
        if self.y - needed < 55:
            self.new_page()
        self.pdf.setFont("Helvetica-Bold", 8)
        self.pdf.drawString(45, self.y, label)
        self.y -= height + 5
        flags = 4096 if multiline else 0
        self.form.textfield(
            name=name,
            x=45,
            y=self.y,
            width=width,
            height=height,
            borderColor=GOLD,
            fillColor=HexColor("#FFFFFF"),
            textColor=INK,
            borderWidth=1,
            forceBorder=True,
            fieldFlags=flags,
            fontName="Helvetica",
            fontSize=9,
        )
        self.y -= 13

    def two_fields(self, left_label, left_name, right_label, right_name):
        if self.y - 46 < 55:
            self.new_page()
        self.pdf.setFont("Helvetica-Bold", 8)
        self.pdf.drawString(45, self.y, left_label)
        self.pdf.drawString(312, self.y, right_label)
        self.y -= 23
        for x, name in ((45, left_name), (312, right_name)):
            self.form.textfield(
                name=name, x=x, y=self.y, width=258, height=18,
                borderColor=GOLD, fillColor=HexColor("#FFFFFF"), textColor=INK,
                borderWidth=1, forceBorder=True, fontName="Helvetica", fontSize=9,
            )
        self.y -= 13

    def check(self, label, name):
        if self.y < 70:
            self.new_page()
        self.form.checkbox(
            name=name, x=45, y=self.y - 3, size=11,
            borderColor=GOLD, fillColor=HexColor("#FFFFFF"), buttonStyle="check",
            forceBorder=True,
        )
        self.pdf.setFont("Helvetica", 8.5)
        self.pdf.drawString(62, self.y, label)
        self.y -= 19

    def save(self):
        self.footer()
        self.pdf.save()


def build_application(path):
    doc = FillableForm(
        path,
        "RENTALREADYPRO RENTAL APPLICATION",
        "Reusable application for standard whole-property rentals. No application fee is charged by this form.",
    )
    doc.section("Property requested")
    doc.field("Property address", "property_address")
    doc.two_fields("Requested move-in date", "move_in_date", "Requested monthly rent", "requested_rent")
    doc.section("Applicant")
    doc.two_fields("Legal name", "applicant_name", "Preferred name", "preferred_name")
    doc.two_fields("Phone", "phone", "Email", "email")
    doc.two_fields("Date of birth", "date_of_birth", "Government ID type", "id_type")
    doc.field("Current address", "current_address")
    doc.two_fields("Time at address", "current_address_length", "Current monthly rent", "current_rent")
    doc.two_fields("Current landlord / manager", "current_landlord", "Landlord phone or email", "current_landlord_contact")
    doc.section("Household")
    doc.field("Every proposed occupant and relationship to applicant", "occupants", height=52, multiline=True)
    doc.field("Animals or requested assistance-animal accommodation (do not disclose a diagnosis)", "animals", height=40, multiline=True)
    doc.section("Residence history")
    doc.field("Previous address", "previous_address")
    doc.two_fields("Dates at previous address", "previous_dates", "Previous monthly rent", "previous_rent")
    doc.two_fields("Previous landlord / manager", "previous_landlord", "Landlord phone or email", "previous_landlord_contact")
    doc.field("Explain any material rental-history issue you want considered, including corrective steps", "rental_history_context", height=70, multiline=True)
    doc.section("Income and ability to pay")
    doc.two_fields("Employer / income source", "income_source", "Position or benefit type", "position")
    doc.two_fields("Gross monthly income", "monthly_income", "Length of employment / income", "income_length")
    doc.field("Other lawful income you want considered (optional)", "other_income")
    doc.field("Income-verification documents provided", "income_documents")
    doc.section("References")
    doc.two_fields("Reference 1 name", "reference_1_name", "Reference 1 phone/email", "reference_1_contact")
    doc.two_fields("Reference 2 name", "reference_2_name", "Reference 2 phone/email", "reference_2_contact")
    doc.section("Screening notice and authorization")
    doc.note(
        "There is no application fee. A background check is required before final approval for every serious contender. "
        "Submitting this application does not guarantee approval. The housing provider will disclose its written criteria "
        "and any screening provider before ordering a consumer report. Criminal-history information is not automatically "
        "scored or rejected; legally required supplemental evidence and individualized review will be provided."
    )
    doc.check("I authorize verification of the application information and rental references.", "authorize_verification")
    doc.check("After receiving the required disclosures, I authorize the housing provider to obtain tenant-screening reports.", "authorize_screening")
    doc.check("I understand that a background check is required before final approval.", "background_required_ack")
    doc.field("Information or supplemental evidence I want considered", "supplemental_evidence", height=85, multiline=True)
    doc.section("Certification")
    doc.note("I certify that the information supplied is complete and accurate. Electronic signatures are intended to have the same effect as handwritten signatures where permitted by law.")
    doc.two_fields("Applicant signature", "applicant_signature", "Date", "application_date")
    doc.save()


def build_agreement(path):
    doc = FillableForm(
        path,
        "RENTALREADYPRO RESIDENTIAL RENTAL AGREEMENT",
        "Reusable Oregon working template. Complete property-specific terms and obtain legal review before use.",
    )
    doc.section("Parties and premises")
    doc.two_fields("Housing provider / landlord", "landlord_name", "Property owner", "owner_name")
    doc.field("Landlord notice address", "landlord_notice_address")
    doc.field("Rental property address", "property_address")
    doc.field("Every adult tenant", "adult_tenants", height=40, multiline=True)
    doc.field("Authorized minor occupants", "minor_occupants", height=32, multiline=True)
    doc.section("Term")
    doc.check("Month-to-month tenancy", "term_month_to_month")
    doc.check("Fixed term tenancy", "term_fixed")
    doc.two_fields("Start date", "start_date", "Fixed-term end date, if any", "end_date")
    doc.section("Rent and deposits")
    doc.two_fields("Monthly rent", "monthly_rent", "Rent due day", "rent_due_day")
    doc.field("Authorized payment methods and delivery location", "payment_methods")
    doc.two_fields("Security deposit", "security_deposit", "Prepaid rent, if any", "prepaid_rent")
    doc.field("Lawful late-charge method and amount", "late_charge")
    doc.note("No application fee is part of this rental agreement. Deposits, rent, and other charges must be handled and documented as required by current law.")
    doc.section("Utilities and services")
    doc.field("Tenant-paid utilities and providers", "tenant_utilities", height=42, multiline=True)
    doc.field("Owner-paid utilities and services", "owner_utilities", height=42, multiline=True)
    doc.field("Utility allocation or billing method, if applicable", "utility_method", height=42, multiline=True)
    doc.section("Use, condition, and rules")
    doc.field("Parking, storage, keys, and access devices", "parking_storage_keys", height=45, multiline=True)
    doc.field("Animals and assistance-animal accommodations", "animals", height=40, multiline=True)
    doc.field("Smoking or vaping policy", "smoking_policy", height=35, multiline=True)
    doc.field("Property-specific rules incorporated into this agreement", "property_rules", height=75, multiline=True)
    doc.note("Tenant will use the premises as a residence, keep it reasonably clean and safe, promptly report damage or unsafe conditions, and avoid conduct that unlawfully interferes with neighbors or damages property.")
    doc.section("Maintenance, entry, and insurance")
    doc.field("Owner-provided appliances and equipment", "appliances", height=40, multiline=True)
    doc.field("Maintenance request method and emergency contact", "maintenance_contact", height=40, multiline=True)
    doc.note("Landlord entry, repairs, habitability duties, smoke and carbon-monoxide alarms, and tenant remedies are governed by current Oregon law. Nothing in this agreement waives a nonwaivable right or duty.")
    doc.two_fields("Renters insurance required?", "insurance_required", "Minimum liability coverage", "insurance_coverage")
    doc.section("Notices, screening, and incorporated documents")
    doc.field("Address or electronic method authorized for notices, if lawful", "notice_method", height=40, multiline=True)
    doc.field("Addenda and disclosures attached to this agreement", "addenda", height=70, multiline=True)
    doc.note("Any termination, rent increase, entry notice, fee, deposit accounting, or other legal notice must follow the law in effect when the notice is given. A background check is an application-stage requirement and is not a continuing authorization after tenancy begins unless separately authorized by law.")
    doc.section("Signatures")
    doc.note("The parties acknowledge receipt of a completed copy and agree to the filled terms and incorporated addenda. Electronic signatures are intended to have the same effect as handwritten signatures where permitted by law.")
    doc.two_fields("Tenant 1 signature", "tenant_1_signature", "Date", "tenant_1_date")
    doc.two_fields("Tenant 2 signature", "tenant_2_signature", "Date", "tenant_2_date")
    doc.two_fields("Landlord / agent signature", "landlord_signature", "Date", "landlord_date")
    doc.save()


class Command(BaseCommand):
    help = "Generate the reusable fillable standard-rental application and agreement PDFs."

    def handle(self, *args, **options):
        output_dir = Path(settings.BASE_DIR) / "static" / "forms"
        output_dir.mkdir(parents=True, exist_ok=True)
        application_path = output_dir / "rentalreadypro_standard_rental_application.pdf"
        agreement_path = output_dir / "rentalreadypro_standard_rental_agreement.pdf"
        build_application(application_path)
        build_agreement(agreement_path)
        self.stdout.write(self.style.SUCCESS(f"Created {application_path}"))
        self.stdout.write(self.style.SUCCESS(f"Created {agreement_path}"))
