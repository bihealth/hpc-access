# Generated by Django 4.2.11 on 2024-06-12 07:57

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("usersec", "0025_remove_hpcgroup_folder_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="TermsAndConditions",
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
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, help_text="Record UUID", unique=True
                    ),
                ),
                (
                    "date_created",
                    models.DateTimeField(
                        auto_now_add=True, help_text="DateTime of creation"
                    ),
                ),
                ("date_modified", models.DateTimeField(auto_now=True)),
                (
                    "title",
                    models.CharField(
                        help_text="Title of this terms and conditions leg.",
                        max_length=512,
                    ),
                ),
                (
                    "text",
                    models.TextField(
                        help_text="Text of this terms and conditions leg."
                    ),
                ),
                (
                    "audience",
                    models.CharField(
                        choices=[("user", "user"), ("pi", "pi"), ("all", "all")],
                        default="all",
                        help_text="Define the target audience of the text.",
                        max_length=16,
                    ),
                ),
                (
                    "date_published",
                    models.DateTimeField(
                        blank=True, help_text="Date of publication.", null=True
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
