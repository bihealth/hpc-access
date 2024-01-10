# Generated by Django 4.0.3 on 2022-04-01 14:51

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("usersec", "0006_remove_hpcuser_email_remove_hpcuser_first_names_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="hpcusercreaterequest",
            name="email",
            field=models.CharField(
                default="user@example.com",
                help_text="Email of user to send an invitation to",
                max_length=255,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="hpcusercreaterequest",
            name="group",
            field=models.ForeignKey(
                help_text="Group the request belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s",
                to="usersec.hpcgroup",
            ),
        ),
        migrations.AddField(
            model_name="hpcusercreaterequestversion",
            name="email",
            field=models.CharField(
                default="user@example.com",
                help_text="Email of user to send an invitation to",
                max_length=255,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="hpcusercreaterequestversion",
            name="group",
            field=models.ForeignKey(
                help_text="Group the request belongs to",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="%(class)s",
                to="usersec.hpcgroup",
            ),
        ),
    ]
