# Generated by Django 4.0.2 on 2022-03-28 15:30

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_hpcadmin",
            field=models.BooleanField(
                default=False,
                help_text="Designates whether the user is an HPC admin.",
                verbose_name="HPC admin status",
            ),
        ),
    ]
