from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

# ---------------------------------------------------------
# OWNER PROFILE (Landlord / Admin User)
# ---------------------------------------------------------
class OwnerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.company_name if self.company_name else self.user.username


# ---------------------------------------------------------
# PROPERTY (Owned by an OwnerProfile)
# ---------------------------------------------------------
class Property(models.Model):
    owner = models.ForeignKey(OwnerProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    address = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)  # for future property photos

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.owner})"


# ---------------------------------------------------------
# UNIT / ROOM (Belongs to a Property)
# ---------------------------------------------------------
class Unit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    unit_number = models.CharField(max_length=50)
    is_occupied = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.property.name} – Unit {self.unit_number}"


# ---------------------------------------------------------
# RESIDENT PROFILE (Approved applicant living in a unit)
# ---------------------------------------------------------
class Resident(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)
    move_in_date = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} – {self.property.name}"


# ---------------------------------------------------------
# APPLICATION (Submitted by a prospective resident)
# ---------------------------------------------------------
class Application(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    full_name = models.CharField(max_length=200)
    dob = models.DateField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    income = models.CharField(max_length=200)
    current_address = models.CharField(max_length=300)
    emergency_contact = models.CharField(max_length=200)
    background_info = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New'),
            ('reviewing', 'Reviewing'),
            ('approved', 'Approved'),
            ('denied', 'Denied'),
        ],
        default='new'
    )

    def __str__(self):
        return f"Application from {self.full_name} for {self.property.name}"


# ---------------------------------------------------------
# LEASE (Resident + Unit + Property)
# ---------------------------------------------------------
class Lease(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    monthly_rent = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"Lease for {self.resident.user.username} – Unit {self.unit.unit_number}"

