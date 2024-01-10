# Generated by Django 4.0.2 on 2022-03-22 18:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("usersec", "0003_link_version_objects_to_nonversion_objects"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="hpcgroupcreaterequest",
            name="delegate_email",
        ),
        migrations.RemoveField(
            model_name="hpcgroupcreaterequest",
            name="member_emails",
        ),
        migrations.RemoveField(
            model_name="hpcgroupcreaterequestversion",
            name="delegate_email",
        ),
        migrations.RemoveField(
            model_name="hpcgroupcreaterequestversion",
            name="member_emails",
        ),
        migrations.AlterField(
            model_name="hpcgroup",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                default="INITIAL",
                help_text="Status of the group object",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupchangerequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupchangerequestversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupcreaterequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupcreaterequestversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupdeleterequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupdeleterequestversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcgroupversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                default="INITIAL",
                help_text="Status of the group object",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuser",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                default="INITIAL",
                help_text="Status of the user object",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuserchangerequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuserchangerequestversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcusercreaterequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcusercreaterequestversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuserdeleterequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuserdeleterequestversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("REVISION", "REVISION"),
                    ("REVISED", "REVISED"),
                    ("APPROVED", "APPROVED"),
                    ("DENIED", "DENIED"),
                    ("RETRACTED", "RETRACTED"),
                ],
                default="INITIAL",
                help_text="Status of the request",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="hpcuserversion",
            name="status",
            field=models.CharField(
                choices=[
                    ("INITIAL", "INITIAL"),
                    ("ACTIVE", "ACTIVE"),
                    ("DELETED", "DELETED"),
                    ("EXPIRED", "EXPIRED"),
                ],
                default="INITIAL",
                help_text="Status of the user object",
                max_length=16,
            ),
        ),
    ]
