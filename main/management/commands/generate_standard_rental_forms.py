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
    def __init__(self, path, title, subtitle, auto_size_text=False):
        self.path = path
        self.title = title
        self.subtitle = subtitle
        self.field_font_size = 0 if auto_size_text else 9
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
        needed = max(height, (len(lines) * 11) + 5)
        if self.y - needed < 55:
            self.new_page()
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
            fontSize=self.field_font_size,
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
                borderWidth=1, forceBorder=True, fontName="Helvetica", fontSize=self.field_font_size,
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
        auto_size_text=True,
    )
    doc.section("Property requested")
    doc.field("Property address", "property_address")
    doc.two_fields("Requested move-in date", "move_in_date", "Requested monthly rent", "requested_rent")
    doc.section("Applicant 1 - identity and contact")
    doc.two_fields("Legal name", "applicant_name", "Preferred name", "preferred_name")
    doc.two_fields("Phone", "phone", "Email", "email")
    doc.two_fields("Date of birth", "date_of_birth", "Government ID type", "id_type")
    doc.field("Current address", "current_address")
    doc.two_fields("Time at address", "current_address_length", "Current monthly rent", "current_rent")
    doc.two_fields("Current landlord / manager", "current_landlord", "Landlord phone or email", "current_landlord_contact")
    doc.section("Applicant 1 - residence history")
    doc.field("Previous address", "previous_address")
    doc.two_fields("Dates at previous address", "previous_dates", "Previous monthly rent", "previous_rent")
    doc.two_fields("Previous landlord / manager", "previous_landlord", "Landlord phone or email", "previous_landlord_contact")
    doc.field("Explain any material rental-history issue you want considered, including corrective steps", "rental_history_context", height=70, multiline=True)
    doc.section("Applicant 1 - income and ability to pay")
    doc.two_fields("Employer / income source", "income_source", "Position or benefit type", "position")
    doc.two_fields("Gross monthly income", "monthly_income", "Length of employment / income", "income_length")
    doc.field("Other lawful income you want considered (optional)", "other_income")
    doc.field("Income-verification documents provided", "income_documents")
    doc.section("Applicant 1 - references")
    doc.two_fields("Reference 1 name", "reference_1_name", "Reference 1 phone/email", "reference_1_contact")
    doc.two_fields("Reference 2 name", "reference_2_name", "Reference 2 phone/email", "reference_2_contact")
    doc.section("Applicant 2 - identity and contact")
    doc.two_fields("Legal name", "applicant_2_name", "Preferred name", "applicant_2_preferred_name")
    doc.two_fields("Phone", "applicant_2_phone", "Email", "applicant_2_email")
    doc.two_fields("Date of birth", "applicant_2_date_of_birth", "Government ID type", "applicant_2_id_type")
    doc.field("Current address", "applicant_2_current_address")
    doc.two_fields("Time at address", "applicant_2_current_address_length", "Current monthly rent", "applicant_2_current_rent")
    doc.two_fields("Current landlord / manager", "applicant_2_current_landlord", "Landlord phone or email", "applicant_2_current_landlord_contact")
    doc.section("Applicant 2 - residence history")
    doc.field("Previous address", "applicant_2_previous_address")
    doc.two_fields("Dates at previous address", "applicant_2_previous_dates", "Previous monthly rent", "applicant_2_previous_rent")
    doc.two_fields("Previous landlord / manager", "applicant_2_previous_landlord", "Landlord phone or email", "applicant_2_previous_landlord_contact")
    doc.field("Explain any material rental-history issue you want considered, including corrective steps", "applicant_2_rental_history_context", height=70, multiline=True)
    doc.section("Applicant 2 - income and ability to pay")
    doc.two_fields("Employer / income source", "applicant_2_income_source", "Position or benefit type", "applicant_2_position")
    doc.two_fields("Gross monthly income", "applicant_2_monthly_income", "Length of employment / income", "applicant_2_income_length")
    doc.field("Other lawful income you want considered (optional)", "applicant_2_other_income")
    doc.field("Income-verification documents provided", "applicant_2_income_documents")
    doc.section("Applicant 2 - references")
    doc.two_fields("Reference 1 name", "applicant_2_reference_1_name", "Reference 1 phone/email", "applicant_2_reference_1_contact")
    doc.two_fields("Reference 2 name", "applicant_2_reference_2_name", "Reference 2 phone/email", "applicant_2_reference_2_contact")
    doc.section("Household")
    doc.field("Every proposed occupant and relationship to the applicants", "occupants", height=52, multiline=True)
    doc.field("Animals or requested assistance-animal accommodation (do not disclose a diagnosis)", "animals", height=40, multiline=True)
    doc.field("Vehicles to be kept at the property (year, make, model, color, plate)", "vehicles", height=45, multiline=True)
    doc.two_fields("Emergency contact name", "emergency_contact_name", "Emergency contact phone/email", "emergency_contact_details")
    doc.section("Guarantor, if requested after review")
    doc.note("Complete this section only if the housing provider requests a guarantor. A guarantor must sign a separate written guaranty before being bound.")
    doc.two_fields("Guarantor legal name", "guarantor_name", "Relationship to applicant", "guarantor_relationship")
    doc.two_fields("Phone", "guarantor_phone", "Email", "guarantor_email")
    doc.field("Mailing address", "guarantor_address")
    doc.two_fields("Employer / income source", "guarantor_income_source", "Gross monthly income", "guarantor_monthly_income")
    doc.section("Screening notice and authorization")
    doc.note(
        "There is no application fee. A background check is required before final approval for every serious contender. "
        "Submitting this application does not guarantee approval. The housing provider will disclose its written criteria "
        "and any screening provider before ordering a consumer report. Criminal-history information is not automatically "
        "scored or rejected; legally required supplemental evidence and individualized review will be provided."
    )
    doc.check("Applicant 1 authorizes verification of application information and rental references.", "applicant_1_authorize_verification")
    doc.check("Applicant 1 authorizes tenant-screening reports after receiving the required disclosures.", "applicant_1_authorize_screening")
    doc.check("Applicant 1 understands that a background check is required before final approval.", "applicant_1_background_required_ack")
    doc.check("Applicant 2 authorizes verification of application information and rental references.", "applicant_2_authorize_verification")
    doc.check("Applicant 2 authorizes tenant-screening reports after receiving the required disclosures.", "applicant_2_authorize_screening")
    doc.check("Applicant 2 understands that a background check is required before final approval.", "applicant_2_background_required_ack")
    doc.field("Information or supplemental evidence I want considered", "supplemental_evidence", height=85, multiline=True)
    doc.section("Certification")
    doc.note("Each applicant certifies that the information supplied is complete and accurate. Electronic signatures are intended to have the same effect as handwritten signatures where permitted by law.")
    doc.field("Applicant 1 printed / typed legal name", "applicant_1_printed_name")
    doc.two_fields("Applicant 1 signature", "applicant_signature", "Date", "application_date")
    doc.field("Applicant 2 printed / typed legal name", "applicant_2_printed_name")
    doc.two_fields("Applicant 2 signature", "applicant_2_signature", "Date", "applicant_2_application_date")
    doc.save()


def build_agreement(path):
    doc = FillableForm(
        path,
        "RENTALREADYPRO RESIDENTIAL RENTAL AGREEMENT",
        "Reusable Oregon working template. Complete every applicable field and attach required disclosures before use.",
        auto_size_text=True,
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
    doc.field("Late charge: select one lawful method, state the amount, and state when it becomes due", "late_charge", height=34, multiline=True)
    doc.note(
        "No application fee is charged. Rent is delinquent only as provided by Oregon law. Any late charge must be "
        "written here and comply with ORS 90.260. The landlord will provide a receipt for the security deposit and, "
        "after the tenancy ends and possession is returned, will provide the accounting and refund required by law."
    )
    doc.section("Utilities and services")
    doc.field("Tenant-paid utilities and providers", "tenant_utilities", height=42, multiline=True)
    doc.field("Owner-paid utilities and services", "owner_utilities", height=42, multiline=True)
    doc.field("Utility allocation or billing method, if applicable", "utility_method", height=42, multiline=True)
    doc.field("Internet, garbage, yard care, and other recurring responsibilities", "other_services", height=42, multiline=True)
    doc.section("Use, condition, and rules")
    doc.field("Parking, storage, keys, and access devices", "parking_storage_keys", height=45, multiline=True)
    doc.field("Animals and assistance-animal accommodations", "animals", height=40, multiline=True)
    doc.field("Smoking and vaping policy for the dwelling, grounds, and common areas", "smoking_policy", height=35, multiline=True)
    doc.field("Property-specific rules incorporated into this agreement", "property_rules", height=75, multiline=True)
    doc.note(
        "The premises may be occupied only by the authorized occupants. Subletting, assignment, and short-term rental "
        "use are prohibited without the landlord's prior written approval. A guest who is not named in this agreement "
        "may not stay overnight for more than five consecutive calendar days without prior written approval. The "
        "landlord is willing to consider reasonable exceptions when requested in advance; tenants must communicate "
        "promptly and keep the landlord informed."
    )
    doc.note(
        "Tenant will use the premises as a residence, keep it reasonably clean and safe, promptly report damage or "
        "unsafe conditions, and avoid conduct that unlawfully interferes with neighbors or damages property. Normal "
        "wear is not tenant damage. No alteration, additional lock, painting, or fixture installation may be made "
        "without prior written approval, except as otherwise allowed by law."
    )
    doc.section("Maintenance, entry, and insurance")
    doc.field("Owner-provided appliances and equipment", "appliances", height=40, multiline=True)
    doc.field("Maintenance request method and emergency contact", "maintenance_contact", height=40, multiline=True)
    doc.note(
        "Landlord entry, repairs, habitability duties, smoke and carbon-monoxide alarms, and tenant remedies are "
        "governed by current Oregon law. Except for emergencies and other lawful exceptions, entry requires the "
        "notice and reasonable timing required by ORS 90.322. Nothing in this agreement waives a nonwaivable right or duty."
    )
    doc.two_fields("Renters insurance required?", "insurance_required", "Minimum liability coverage", "insurance_coverage")
    doc.note(
        "If renters insurance is required, it covers the tenant's personal property and personal liability. The tenant "
        "is not responsible for insuring the building itself. Insurance requirements do not make a tenant responsible "
        "for loss that is not legally attributable to the tenant."
    )
    doc.section("Condition and move-in records")
    doc.field("Move-in inspection date and participants", "move_in_inspection")
    doc.field("Existing damage or condition notes; attach a signed checklist and photographs when available", "condition_notes", height=75, multiline=True)
    doc.two_fields("Number of dwelling keys", "dwelling_keys", "Other keys / remotes / devices", "other_access_devices")
    doc.section("Notices, screening, and incorporated documents")
    doc.field("Address or electronic method authorized for notices, if lawful", "notice_method", height=40, multiline=True)
    doc.field("Addenda and disclosures attached to this agreement", "addenda", height=70, multiline=True)
    doc.check("Smoking-policy disclosure is completed above or in an attached addendum.", "smoking_disclosure_attached")
    doc.check("Lead-based paint disclosure is attached if the dwelling was built before 1978 and the law requires it.", "lead_disclosure_attached")
    doc.check("Move-in condition checklist is attached or will be completed at possession.", "condition_checklist_attached")
    doc.note("Any termination, rent increase, entry notice, fee, deposit accounting, or other legal notice must follow the law in effect when the notice is given. A background check is an application-stage requirement and is not a continuing authorization after tenancy begins unless separately authorized by law.")
    doc.section("Signatures")
    doc.note("The parties acknowledge receipt of a completed copy and agree to the filled terms and incorporated addenda. Electronic signatures are intended to have the same effect as handwritten signatures where permitted by law.")
    doc.field("Tenant 1 printed / typed legal name", "tenant_1_printed_name")
    doc.two_fields("Tenant 1 signature", "tenant_1_signature", "Date", "tenant_1_date")
    doc.field("Tenant 2 printed / typed legal name", "tenant_2_printed_name")
    doc.two_fields("Tenant 2 signature", "tenant_2_signature", "Date", "tenant_2_date")
    doc.field("Tenant 3 printed / typed legal name, if any", "tenant_3_printed_name")
    doc.two_fields("Tenant 3 signature", "tenant_3_signature", "Date", "tenant_3_date")
    doc.field("Landlord / authorized agent printed / typed name", "landlord_printed_name")
    doc.two_fields("Landlord / authorized agent signature", "landlord_signature", "Date", "landlord_date")
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
