import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_property_address_property_available_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='housingapplication',
            name='current_address',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='current_address_length',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='drivers_license_number',
            field=models.CharField(blank=True, max_length=100, verbose_name='Oregon Driver License Number'),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='drug_of_choice',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='employer_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='employment_length',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='felony_history',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='has_valid_odl',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='id_upload',
            field=models.FileField(blank=True, null=True, upload_to='application_ids/'),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='in_recovery',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='odoc_time_served',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='on_parole',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='oregon_id_number',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='parole_officer_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='parole_officer_phone',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='previous_address_1',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='previous_address_1_length',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='previous_address_2',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='previous_address_2_length',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='previous_address_3',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='previous_address_3_length',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='previous_evictions',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='property',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='applications', to='main.property'),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_1_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_1_phone',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_1_relationship',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_1_type',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_2_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_2_phone',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_2_relationship',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='reference_2_type',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='sobriety_acknowledgment',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='housingapplication',
            name='unconditional_regard_acknowledgment',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='property',
            name='availability_message',
            field=models.CharField(default='Join Waitlist for Availability', max_length=255),
        ),
        migrations.AddField(
            model_name='property',
            name='availability_status',
            field=models.CharField(choices=[('available', 'Available Now'), ('waitlist', 'Waitlist Open'), ('full', 'Currently Full')], default='full', max_length=20),
        ),
        migrations.CreateModel(
            name='ApplicantDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('lease', 'Lease Agreement'), ('application_pdf', 'Application PDF'), ('id', 'Identification'), ('onboarding', 'Onboarding Document'), ('other', 'Other')], max_length=50)),
                ('file', models.FileField(upload_to='applicant_documents/')),
                ('name', models.CharField(max_length=255)),
                ('status', models.CharField(choices=[('draft', 'Draft / Uploaded'), ('sent', 'Sent to Applicant'), ('review', 'Under Review'), ('signed', 'Signed / Completed'), ('locked', 'Locked (Final)')], default='draft', max_length=20)),
                ('needs_signature', models.BooleanField(default=False)),
                ('needs_initials', models.BooleanField(default=False)),
                ('signed_at', models.DateTimeField(blank=True, null=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('locked', models.BooleanField(default=False)),
                ('landlord_notified', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='main.housingapplication')),
            ],
        ),
    ]
