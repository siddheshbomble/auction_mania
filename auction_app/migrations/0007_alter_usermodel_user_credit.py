# Generated by Django 4.2.16 on 2024-12-14 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auction_app", "0006_rename_credits_usermodel_user_credit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usermodel",
            name="user_credit",
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]
