# Generated by Django 4.2.16 on 2024-12-16 05:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auction_app", "0012_alter_bidmodel_bidder_alter_bidmodel_item"),
    ]

    operations = [
        migrations.AlterField(
            model_name="itemmodel",
            name="item_image",
            field=models.ImageField(upload_to="pictures/"),
        ),
    ]
