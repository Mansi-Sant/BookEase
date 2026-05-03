from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizer", "0002_service_appointment_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="venue",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="appointmentslot",
            name="day_of_week",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="bookingrule",
            name="manage_capacity",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="bookingrule",
            name="advance_payment_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
