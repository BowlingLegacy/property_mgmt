from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ("tenant", "Tenant / Applicant"),
        ("landlord", "Landlord / Property Manager"),
        ("admin", "Platform Admin"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="tenant")
    invite_code = models.CharField(max_length=6, blank=True, null=True, unique=True)

    def __str__(self):
        return self.username


class Property(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="property_photos/", blank=True, null=True)

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

availability_status = models.CharField(
    max_length=20,
    choices=AVAILABILITY_CHOICES,
    default="full"
)

availability_message = models.CharField(
    max_length=255,
    default="Join Waitlist for Availability"
)

    

    def __str__(self):
        return self.name


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images"
    )
    image = models.ImageField(upload_to="property_gallery/")
    caption = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.property.name} Image"


class HousingApplication(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications"
    )

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    age = models.PositiveIntegerField()

    current_address = models.CharField(max_length=255, blank=True)
    current_address_length = models.CharField(max_length=100, blank=True)

    previous_address_1 = models.CharField(max_length=255, blank=True)
    previous_address_1_length = models.CharField(max_length=100, blank=True)

    previous_address_2 = models.CharField(max_length=255, blank=True)
    previous_address_2_length = models.CharField(max_length=100, blank=True)

    previous_address_3 = models.CharField(max_length=255, blank=True)
    previous_address_3_length = models.CharField(max_length=100, blank=True)

    drivers_license_number = models.CharField("Oregon Driver License Number", max_length=100, blank=True)
    has_valid_odl = models.BooleanField("Is this Oregon Driver License valid?", default=False)
    oregon_id_number = models.CharField("Oregon ID Number if no ODL", max_length=100, blank=True)
    id_upload = models.FileField(
        "Upload photo of ID or Driver License",
        upload_to="application_ids/",
        blank=True,
        null=True
    )

    income_source = models.CharField(max_length=255)
    monthly_income = models.DecimalField(max_digits=10, decimal_places=2)
    employer_name = models.CharField(max_length=255, blank=True)
    employment_length = models.CharField(max_length=100, blank=True)

    previous_evictions = models.TextField("Any previous evictions? Please explain.", blank=True)

    in_recovery = models.BooleanField("Are you in recovery?", default=False)
    drug_of_choice = models.CharField(max_length=255, blank=True)

    on_parole = models.BooleanField(
        "Are you currently on parole? This does not automatically impact tenancy.",
        default=False
    )
    parole_officer_name = models.CharField(max_length=255, blank=True)
    parole_officer_phone = models.CharField(max_length=50, blank=True)

    felony_history = models.TextField(
        "Felony history, if any. This does not disqualify you; it helps us understand housing barriers and support needs.",
        blank=True
    )
    odoc_time_served = models.BooleanField("Have you served time with ODOC?", default=False)

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

    def __str__(self):
        return self.full_name


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
