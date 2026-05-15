from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.conf import settings
import random
import string


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class BlogComment(models.Model):
    post = models.ForeignKey("BlogPost", on_delete=models.CASCADE, related_name="comments")
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    comment = models.TextField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Comment by {self.name} on {self.post.title}"


class User(AbstractUser):
    ROLE_CHOICES = [
        ("tenant", "Tenant / Applicant"),
        ("landlord", "Landlord / Property Manager"),
        ("assistant", "Assistant"),
        ("admin", "Platform Admin"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="tenant")
    invite_code = models.CharField(max_length=6, blank=True, null=True, unique=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if not self.invite_code:
            self.invite_code = self.generate_unique_code()

        if self.role == "tenant":
            self.is_staff = False
            self.is_superuser = False

        super().save(*args, **kwargs)

        if is_new and self.email and self.invite_code:
            send_mail(
                "Your Bowling Legacy Resident Portal Access Code",
                f"""Hello {self.username},

Your Bowling Legacy resident portal access code is:

{self.invite_code}

Portal login:
https://bowlinglegacy.com/login/

Thank you,
Bowling Legacy Housing
""",
                getattr(settings, "DEFAULT_FROM_EMAIL", None),
                [self.email],
                fail_silently=True,
            )

    def generate_unique_code(self):
        while True:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not User.objects.filter(invite_code=code).exists():
                return code

    def __str__(self):
        return self.username


class Property(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="property_photos/", blank=True, null=True)

    owner_email = models.EmailField(blank=True)

    unit_size = models.CharField(max_length=100, blank=True)
    cable_ready = models.BooleanField(default=True)
    available_date = models.DateField(blank=True, null=True)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    utilities_cost = models.CharField(max_length=255, blank=True)

    AVAILABILITY_CHOICES = [
        ("available", "Available Now"),
        ("waitlist", "Waitlist Open"),
        ("full", "Currently Full"),
    ]

    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default="full")
    availability_message = models.CharField(max_length=255, default="Join Waitlist for Availability")

    def __str__(self):
        return self.name


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="property_gallery/")
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.property.name} Image"


class HousingApplication(models.Model):
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name="applications")
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resident_profile")

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    age = models.PositiveIntegerField()

    space_type = models.CharField(max_length=50, blank=True)
    space_label = models.CharField(max_length=50, blank=True)

    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    rent_due_day = models.IntegerField(default=1)
    
    lease_start_date = models.DateField(blank=True, null=True)

    deposit_required = models.DecimalField(max_digits=10, decimal_places=2, default=450.00)
    deposit_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    utility_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=66.00)
    utility_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    current_address = models.CharField(max_length=255, blank=True)
    current_address_length = models.CharField(max_length=100, blank=True)
    previous_address_1 = models.CharField(max_length=255, blank=True)
    previous_address_1_length = models.CharField(max_length=100, blank=True)
    previous_address_2 = models.CharField(max_length=255, blank=True)
    previous_address_2_length = models.CharField(max_length=100, blank=True)
    previous_address_3 = models.CharField(max_length=255, blank=True)
    previous_address_3_length = models.CharField(max_length=100, blank=True)

    drivers_license_number = models.CharField(max_length=100, blank=True)
    has_valid_odl = models.BooleanField(default=False)
    oregon_id_number = models.CharField(max_length=100, blank=True)
    id_upload = models.FileField(upload_to="application_ids/", blank=True, null=True)

    income_source = models.CharField(max_length=255)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2)
    employer_name = models.CharField(max_length=255, blank=True)
    employment_length = models.CharField(max_length=100, blank=True)

    previous_evictions = models.TextField(blank=True)
    in_recovery = models.BooleanField(default=False)
    drug_of_choice = models.CharField(max_length=255, blank=True)

    on_parole = models.BooleanField(default=False)
    parole_officer_name = models.CharField(max_length=255, blank=True)
    parole_officer_phone = models.CharField(max_length=50, blank=True)

    felony_history = models.TextField(blank=True)
    odoc_time_served = models.BooleanField(default=False)

    reference_1_name = models.CharField(max_length=255, blank=True)
    reference_1_phone = models.CharField(max_length=50, blank=True)
    reference_1_relationship = models.CharField(max_length=255, blank=True)
    reference_1_type = models.CharField(max_length=100, blank=True)

    reference_2_name = models.CharField(max_length=255, blank=True)
    reference_2_phone = models.CharField(max_length=50, blank=True)
    reference_2_relationship = models.CharField(max_length=255, blank=True)
    reference_2_type = models.CharField(max_length=100, blank=True)

    housing_need = models.TextField()
    additional_notes = models.TextField(blank=True)

    sobriety_acknowledgment = models.BooleanField(default=False)
    unconditional_regard_acknowledgment = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def deposit_balance(self):
        remaining = self.deposit_required - self.deposit_paid
        return max(remaining, 0)

    def __str__(self):
        return self.full_name


class ApplicantDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("lease", "Lease Agreement"),
        ("application_pdf", "Application PDF"),
        ("id", "Identification"),
        ("onboarding", "Onboarding Document"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("needs_completion", "Needs Completion"),
        ("needs_signature", "Needs Signature"),
        ("completed", "Completed"),
        ("locked", "Locked Final"),
        ("needs_correction", "Needs Correction"),
    ]

    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES, default="other")
    file = models.FileField(upload_to="applicant_documents/")
    name = models.CharField(max_length=255)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="uploaded", blank=True)
    needs_signature = models.BooleanField(default=False)
    needs_initials = models.BooleanField(default=False)
    signed_at = models.DateTimeField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    locked = models.BooleanField(default=False)
    landlord_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.status in ["completed", "locked"]:
            self.locked = True

        if self.locked:
            self.status = "locked"

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.locked:
            return
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.application.full_name})"

class SignedDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("lease", "Resident Lease Agreement"),
        ("emergency_contact", "Emergency Contact Form"),
        ("painted_lady_acknowledgment", "Painted Lady Acknowledgment"),
        ("lead_disclosure", "Lead Disclosure"),
        ("asbestos_disclosure", "Asbestos Disclosure"),
        ("house_rules", "House Rules"),
        ("other", "Other"),
    ]

    application = models.ForeignKey(
        HousingApplication,
        on_delete=models.CASCADE,
        related_name="signed_documents"
    )

    document_type = models.CharField(
        max_length=50,
        choices=DOCUMENT_TYPE_CHOICES,
        default="other"
    )

    title = models.CharField(max_length=255)

    # ---------------------------------------------------------
    # AUTO-POPULATED LEASE FIELDS
    # ---------------------------------------------------------
    property_name = models.CharField(max_length=255, blank=True)
    property_address = models.CharField(max_length=255, blank=True)

    resident_name = models.CharField(max_length=255, blank=True)

    room_space = models.CharField(max_length=100, blank=True)

    monthly_rent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    utility_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    lease_start_date = models.DateField(blank=True, null=True)

    landlord_name = models.CharField(
        max_length=255,
        default="Michael Bowling"
    )

    landlord_signature = models.CharField(
        max_length=255,
        default="Michael Bowling"
    )

    lease_sent_date = models.DateField(blank=True, null=True)

    # ---------------------------------------------------------
    # RESIDENT ACKNOWLEDGMENTS / INITIALS
    # ---------------------------------------------------------
    rent_initials = models.CharField(max_length=10, blank=True)

    sobriety_initials = models.CharField(max_length=10, blank=True)

    testing_initials = models.CharField(max_length=10, blank=True)

    guest_policy_initials = models.CharField(max_length=10, blank=True)

    cleanliness_initials = models.CharField(max_length=10, blank=True)

    disclosure_initials = models.CharField(max_length=10, blank=True)

    # ---------------------------------------------------------
    # SIGNATURES
    # ---------------------------------------------------------
    resident_signature = models.CharField(
        max_length=255,
        blank=True
    )

    signature_agreement = models.BooleanField(default=False)

    signed_at = models.DateTimeField(blank=True, null=True)

    locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.application.full_name}"

    def save(self, *args, **kwargs):

        # AUTO POPULATE FROM RESIDENT FILE
        if self.application:

            self.resident_name = self.application.full_name

            self.monthly_rent = self.application.monthly_rent

            self.utility_fee = self.application.utility_monthly

            self.security_deposit = self.application.deposit_required
            self.lease_start_date = self.application.lease_start_date
            
            self.room_space = (
                f"{self.application.space_type} "
                f"{self.application.space_label}"
            )

            if self.application.property:
                self.property_name = self.application.property.name
                self.property_address = self.application.property.address

        super().save(*args, **kwargs)


class RentHistory(models.Model):
    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE, related_name="rent_history")
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.full_name} - ${self.rent_amount}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    PAYMENT_TYPE_CHOICES = [
        ("rent", "Rent"),
        ("deposit", "Deposit"),
        ("utility", "Utilities"),
        ("late_fee", "Late Fee"),
        ("other", "Other"),
    ]

    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE, related_name="payments")
    payment_type = models.CharField(max_length=30, choices=PAYMENT_TYPE_CHOICES, default="rent")
    description = models.CharField(max_length=255, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    stripe_session_id = models.CharField(max_length=255, blank=True)
    stripe_payment_intent = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.full_name} - {self.get_payment_type_display()} - ${self.amount} - {self.status}"


class FinancialUpload(models.Model):
    file = models.FileField(upload_to="financial_uploads/")
    name = models.CharField(max_length=255, default="Financial Upload")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parsed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.uploaded_at.date()})"


class FinancialEntry(models.Model):
    ENTRY_TYPE_CHOICES = [
        ("income", "Income"),
        ("operating_expense", "Operating Expense"),
        ("debt_service", "Debt Service"),
        ("capital_expense", "Capital Expense"),
        ("other", "Other"),
    ]

    upload = models.ForeignKey(FinancialUpload, on_delete=models.CASCADE, related_name="entries")
    property_name = models.CharField(max_length=255, blank=True, default="Painted Lady")
    sheet_name = models.CharField(max_length=255)
    row_number = models.IntegerField(default=0)

    entry_date = models.DateField(blank=True, null=True)
    month = models.IntegerField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)

    entry_type = models.CharField(max_length=50, choices=ENTRY_TYPE_CHOICES, default="other")
    category = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["year", "month", "entry_type", "category"]

    def __str__(self):
        return f"{self.get_entry_type_display()} - ${self.amount} - {self.sheet_name}"


class ResidentMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ("maintenance", "Maintenance Request"),
        ("complaint", "Complaint"),
        ("general", "General Message"),
        ("document", "Document Question"),
    ]

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("reviewed", "Reviewed"),
        ("closed", "Closed"),
    ]

    application = models.ForeignKey(HousingApplication, on_delete=models.CASCADE, related_name="resident_messages")
    message_type = models.CharField(max_length=30, choices=MESSAGE_TYPE_CHOICES, default="general")
    subject = models.CharField(max_length=255)
    message = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")
    locked = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_message_type_display()} - {self.application.full_name} - {self.created_at}"
