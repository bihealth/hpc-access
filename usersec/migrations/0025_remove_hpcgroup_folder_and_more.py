# Generated by Django 4.2.11 on 2024-05-03 14:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usersec", "0024_rename_group_name_hpcgroupcreaterequest_name_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="hpcgroup",
            name="folder",
        ),
        migrations.RemoveField(
            model_name="hpcgroupcreaterequest",
            name="folder",
        ),
        migrations.RemoveField(
            model_name="hpcgroupcreaterequestversion",
            name="folder",
        ),
        migrations.RemoveField(
            model_name="hpcgroupversion",
            name="folder",
        ),
        migrations.RemoveField(
            model_name="hpcproject",
            name="folder",
        ),
        migrations.RemoveField(
            model_name="hpcprojectcreaterequest",
            name="folder",
        ),
        migrations.RemoveField(
            model_name="hpcprojectcreaterequestversion",
            name="folder",
        ),
        migrations.RemoveField(
            model_name="hpcprojectversion",
            name="folder",
        ),
        migrations.AddField(
            model_name="hpcgroup",
            name="folders",
            field=models.JSONField(
                default={}, help_text="Paths to the folders of the group on the cluster"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="hpcgroupcreaterequest",
            name="folders",
            field=models.JSONField(
                blank=True,
                help_text="Paths to the folders of the project on the cluster",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="hpcgroupcreaterequestversion",
            name="folders",
            field=models.JSONField(
                blank=True,
                help_text="Paths to the folders of the project on the cluster",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="hpcgroupversion",
            name="folders",
            field=models.JSONField(
                default={}, help_text="Paths to the folders of the group on the cluster"
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="hpcproject",
            name="folders",
            field=models.JSONField(
                default={},
                help_text="Paths to the folders of the project on the cluster",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="hpcprojectcreaterequest",
            name="folders",
            field=models.JSONField(
                blank=True,
                help_text="Paths to the folders of the project on the cluster",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="hpcprojectcreaterequestversion",
            name="folders",
            field=models.JSONField(
                blank=True,
                help_text="Paths to the folders of the project on the cluster",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="hpcprojectversion",
            name="folders",
            field=models.JSONField(
                default={},
                help_text="Paths to the folders of the project on the cluster",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="hpcprojectcreaterequest",
            name="description",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Concise description of what kind of computations are required for the project on the cluster",
                ),
                max_length=512,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="hpcprojectcreaterequestversion",
            name="description",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Concise description of what kind of computations are required for the project on the cluster",
                ),
                max_length=512,
                null=True,
            ),
        ),
    ]
