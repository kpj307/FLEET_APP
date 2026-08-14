from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def migrate_existing_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Organization = apps.get_model("api", "Organization")
    Subscription = apps.get_model("api", "Subscription")
    Vehicle = apps.get_model("api", "Vehicle")

    for user in User.objects.all():
        base = slugify(user.username) or f"user-{user.pk}"
        slug = base
        counter = 2

        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1

        organization = Organization.objects.create(
            owner=user,
            name=f"{user.username}'s Fleet",
            slug=slug,
            currency="UGX",
            timezone="Africa/Kampala",
        )

        Subscription.objects.create(
            organization=organization,
            plan="free",
            status="active",
            billing_cycle="monthly",
        )

        Vehicle.objects.filter(owner=user).update(
            organization=organization
        )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255, unique=True)),
                ("currency", models.CharField(default="UGX", max_length=3)),
                (
                    "timezone",
                    models.CharField(
                        default="Africa/Kampala",
                        max_length=64,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "owner",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization",
                        to="auth.user",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "plan",
                    models.CharField(
                        default="free",
                        max_length=30,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        default="active",
                        max_length=30,
                    ),
                ),
                (
                    "billing_cycle",
                    models.CharField(
                        default="monthly",
                        max_length=20,
                    ),
                ),
                (
                    "started_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "expires_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "external_customer_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                    ),
                ),
                (
                    "external_subscription_id",
                    models.CharField(
                        blank=True,
                        max_length=255,
                    ),
                ),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to="api.organization",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="vehicle",
            name="organization",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="vehicles",
                to="api.organization",
            ),
        ),
        migrations.RunPython(
            migrate_existing_users,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="vehicle",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="vehicles",
                to="api.organization",
            ),
        ),
        migrations.AddConstraint(
            model_name="vehicle",
            constraint=models.UniqueConstraint(
                fields=("organization", "plate"),
                name="unique_vehicle_plate_per_organization",
            ),
        ),
        migrations.RemoveField(
            model_name="vehicle",
            name="owner",
        ),
    ]
