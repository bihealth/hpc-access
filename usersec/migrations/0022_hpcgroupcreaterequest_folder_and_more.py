# Generated by Django 4.2.10 on 2024-03-01 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usersec", "0021_hpcgroupcreaterequest_group_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="hpcgroupcreaterequest",
            name="folder",
            field=models.CharField(
                blank=True,
                help_text="Path to the group folder on the cluster",
                max_length=64,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="hpcgroupcreaterequestversion",
            name="folder",
            field=models.CharField(
                blank=True,
                help_text="Path to the group folder on the cluster",
                max_length=64,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupcreaterequest",
            name="group_name",
            field=models.CharField(
                blank=True,
                help_text="POSIX name of the group on the cluster",
                max_length=64,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupcreaterequestversion",
            name="group_name",
            field=models.CharField(
                blank=True,
                help_text="POSIX name of the group on the cluster",
                max_length=64,
                null=True,
            ),
        ),
    ]
