# Generated by Django 5.1 on 2024-08-21 12:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usersec", "0028_alter_hpcprojectcreaterequest_description_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="hpcprojectcreaterequest",
            name="delegate",
            field=models.ForeignKey(
                blank=True,
                help_text="The optional delegate can act on behalf of the project owner",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_delegate",
                to="usersec.hpcuser",
            ),
        ),
        migrations.AddField(
            model_name="hpcprojectcreaterequestversion",
            name="delegate",
            field=models.ForeignKey(
                blank=True,
                help_text="The optional delegate can act on behalf of the project owner",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_delegate",
                to="usersec.hpcuser",
            ),
        ),
    ]