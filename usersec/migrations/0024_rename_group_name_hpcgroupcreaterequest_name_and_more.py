# Generated by Django 4.2.10 on 2024-03-04 17:26

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("usersec", "0023_hpcprojectcreaterequest_folder_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="hpcgroupcreaterequest",
            old_name="group_name",
            new_name="name",
        ),
        migrations.RenameField(
            model_name="hpcgroupcreaterequestversion",
            old_name="group_name",
            new_name="name",
        ),
    ]