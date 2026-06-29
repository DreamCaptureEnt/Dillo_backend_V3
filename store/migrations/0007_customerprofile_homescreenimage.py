from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("store", "0006_product_option_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeScreenImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(blank=True, default="", max_length=180)),
                ("title_ta", models.CharField(blank=True, default="", max_length=220)),
                ("subtitle", models.CharField(blank=True, default="", max_length=240)),
                ("badge", models.CharField(blank=True, default="", max_length=120)),
                ("cta_label", models.CharField(blank=True, default="", max_length=80)),
                ("cta_url", models.CharField(blank=True, default="/products", max_length=180)),
                ("landscape_image", models.CharField(blank=True, default="", max_length=180)),
                ("portrait_image", models.CharField(blank=True, default="", max_length=180)),
                ("caption_label", models.CharField(blank=True, default="", max_length=120)),
                ("caption_subtitle", models.CharField(blank=True, default="", max_length=160)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["sort_order", "id"],
            },
        ),
        migrations.CreateModel(
            name="CustomerProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("phone", models.CharField(max_length=32, unique=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
