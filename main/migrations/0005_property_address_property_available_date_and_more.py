from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_blogpost'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='address',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='property',
            name='available_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='cable_ready',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='property',
            name='deposit_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='unit_size',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='property',
            name='utilities_cost',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
