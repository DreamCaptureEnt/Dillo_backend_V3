from django.db import migrations


def forwards(apps, schema_editor):
    VideoShoppingBooking = apps.get_model("store", "VideoShoppingBooking")
    VideoShoppingBooking.objects.filter(status="confirmed").update(status="pending")


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0003_videoshoppingbooking_attendee_name_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
