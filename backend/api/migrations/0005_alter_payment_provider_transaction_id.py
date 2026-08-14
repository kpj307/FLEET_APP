from django.db import migrations, models


def empty_provider_transaction_ids_to_null(apps, schema_editor):
    Payment = apps.get_model("api", "Payment")

    Payment.objects.filter(
        provider_transaction_id=""
    ).update(
        provider_transaction_id=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_payment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="provider_transaction_id",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
            ),
        ),

        migrations.RunPython(
            empty_provider_transaction_ids_to_null,
            migrations.RunPython.noop,
        ),

        migrations.AlterField(
            model_name="payment",
            name="provider_transaction_id",
            field=models.CharField(
                max_length=255,
                null=True,
                blank=True,
                unique=True,
            ),
        ),
    ]