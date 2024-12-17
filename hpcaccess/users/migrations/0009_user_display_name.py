# Generated by Django 4.2.17 on 2024-12-17 16:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_user_consented_to_terms"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="display_name",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="Display Name"
            ),
        ),
    ]
