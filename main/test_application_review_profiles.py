from decimal import Decimal

from django.test import TestCase

from .models import HousingApplication, Property
from .views import applicant_review_summary


class ApplicationReviewProfileTests(TestCase):
    def create_complete_application(self, property_obj, **overrides):
        values = {
            "property": property_obj,
            "full_name": "Standard Applicant",
            "phone": "541-555-0100",
            "age": 35,
            "monthly_rent": Decimal("1000.00"),
            "utility_monthly": Decimal("150.00"),
            "income_source": "Employment",
            "monthly_income": Decimal("4000.00"),
            "employment_length": "3 years",
            "current_address": "100 Current Street",
            "current_address_length": "2 years",
            "previous_address_1": "200 Previous Street",
            "has_valid_odl": True,
            "reference_1_name": "Prior Landlord",
            "reference_1_phone": "541-555-0111",
            "reference_2_name": "Employer",
            "reference_2_phone": "541-555-0122",
            "housing_need": "Whole-property rental",
            "background_check_required": True,
            "background_check_status": "pending",
        }
        values.update(overrides)
        return HousingApplication.objects.create(**values)

    def test_standard_rental_uses_conventional_factors_and_blocks_final_approval(self):
        property_obj = Property.objects.create(
            name="Belmont",
            application_review_profile="standard_rental",
            requires_background_check=True,
        )
        application = self.create_complete_application(property_obj)

        summary = applicant_review_summary(application)

        self.assertEqual(summary["rating"], "Background Review Required")
        self.assertFalse(summary["eligible_for_final_approval"])
        self.assertNotIn("sobriety", " ".join(summary["review_flags"]).lower())
        self.assertNotIn("parole", " ".join(summary["review_flags"]).lower())
        self.assertNotIn("recovery", " ".join(summary["review_flags"]).lower())

    def test_standard_rental_does_not_auto_reject_background_review(self):
        property_obj = Property.objects.create(
            name="Other Owner Property",
            application_review_profile="standard_rental",
            requires_background_check=True,
        )
        application = self.create_complete_application(property_obj, background_check_status="needs_review")

        summary = applicant_review_summary(application)

        self.assertEqual(summary["rating"], "Background Review Required")
        self.assertIn("individualized assessment", " ".join(summary["review_flags"]).lower())
        self.assertFalse(summary["eligible_for_final_approval"])

    def test_supportive_housing_keeps_painted_lady_review_factors(self):
        property_obj = Property.objects.create(
            name="Painted Lady",
            application_review_profile="supportive_housing",
        )
        application = self.create_complete_application(property_obj, background_check_required=False)

        summary = applicant_review_summary(application)

        self.assertIn("drug- and alcohol-free", " ".join(summary["review_flags"]).lower())
