from django.db import migrations, models


def populate_product_codes(apps, schema_editor):
    Saree = apps.get_model("store", "Saree")
    for saree in Saree.objects.filter(product_code__isnull=True).order_by("id"):
        saree.product_code = f"DILLO-{saree.id:05d}"
        saree.save(update_fields=["product_code"])


def clear_product_codes(apps, schema_editor):
    Saree = apps.get_model("store", "Saree")
    Saree.objects.update(product_code=None)


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0004_convert_confirmed_video_bookings_to_pending"),
    ]

    operations = [
        migrations.AddField(
            model_name="saree",
            name="product_code",
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.RunPython(populate_product_codes, clear_product_codes),
    ]
