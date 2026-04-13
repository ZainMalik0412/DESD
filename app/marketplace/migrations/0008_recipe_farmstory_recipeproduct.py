# Generated migration for Recipe, RecipeProduct, and FarmStory models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import marketplace.services.file_validators


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0007_alter_product_image'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, help_text='Brief description or introduction')),
                ('ingredients', models.TextField(help_text='List of ingredients')),
                ('instructions', models.TextField(help_text='Cooking instructions')),
                ('image', models.ImageField(blank=True, null=True, upload_to='recipes/', validators=[
                    marketplace.services.file_validators.validate_image_file_extension,
                    marketplace.services.file_validators.validate_image_file_size,
                    marketplace.services.file_validators.validate_image_content_type
                ])),
                ('seasonal_tag', models.CharField(
                    choices=[
                        ('spring', 'Spring'),
                        ('summer', 'Summer'),
                        ('autumn_winter', 'Autumn/Winter'),
                        ('all_season', 'All Season')
                    ],
                    default='all_season',
                    max_length=20
                )),
                ('is_published', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('producer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='FarmStory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField(help_text='Story content')),
                ('image', models.ImageField(blank=True, null=True, upload_to='farm_stories/', validators=[
                    marketplace.services.file_validators.validate_image_file_extension,
                    marketplace.services.file_validators.validate_image_file_size,
                    marketplace.services.file_validators.validate_image_content_type
                ])),
                ('is_published', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('producer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='farm_stories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name_plural': 'Farm Stories',
            },
        ),
        migrations.CreateModel(
            name='RecipeProduct',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipe', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='linked_products', to='marketplace.recipe')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipes', to='marketplace.product')),
            ],
            options={
                'unique_together': {('recipe', 'product')},
            },
        ),
    ]
