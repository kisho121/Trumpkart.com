# Generated by Django 5.0.6 on 2024-08-10 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Shop', '0017_carousel'),
    ]

    operations = [
        migrations.AddField(
            model_name='carousel',
            name='alt_text',
            field=models.CharField(default='slide_image', max_length=150),
        ),
    ]
