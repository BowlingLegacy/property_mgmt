from django.db import migrations


BELMONT_FAMILY_HISTORY = (
    "Belmont has been part of the Bowling family story for more than twenty years. "
    "The property was purchased by Jeffery R. Bowling, the younger brother of Bowling "
    "Legacy founder Michael Bowling. Jeffery loved the property and took great pride in "
    "his purchase. Over the years, it became a place where the family gathered to celebrate "
    "holidays and create lasting memories together.\n\n"
    "Jeffery was born on September 19, 1969. He passed away suddenly in July 2010 at forty "
    "years old, shortly before what would have been his forty-first birthday on September 19, "
    "2010. Belmont therefore holds deep personal and sentimental value for the Bowling family. "
    "Keeping the property within Bowling Legacy LLC is a commitment to honor Jeffery's memory "
    "and ensure that a place he loved is cared for by people who understand what it represents.\n\n"
    "Belmont is an established residential duplex in Eugene's Santa Clara area. It includes "
    "two three-bedroom, one-bath homes, each with a single-car garage, along with an extra-large "
    "backyard. Residents maintain their own power, utility, and garbage accounts. Both homes "
    "are currently occupied, and the exact addresses are withheld from the public listing to "
    "respect resident privacy."
)


def correct_jeffery_bowling_year(apps, schema_editor):
    Property = apps.get_model("main", "Property")
    Property.objects.filter(name__iexact="Belmont").update(
        description=BELMONT_FAMILY_HISTORY,
    )


class Migration(migrations.Migration):
    dependencies = [("main", "0083_clarify_jeffery_bowling_dates")]

    operations = [
        migrations.RunPython(
            correct_jeffery_bowling_year,
            migrations.RunPython.noop,
        )
    ]
