# Generated by Django 4.2.11 on 2024-06-10 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_alter_user_email"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="consented_to_terms",
            field=models.BooleanField(
                default=False,
                help_text="User has consented to the latest terms and conditions.",
                verbose_name="Terms consent status",
            ),
        ),
    ]
