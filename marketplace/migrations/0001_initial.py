import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OwnerProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('phone', models.CharField(max_length=30)),
                ('country', models.CharField(max_length=100)),
                ('city', models.CharField(db_index=True, max_length=100)),
                ('address_line1', models.CharField(max_length=255)),
                ('address_line2', models.CharField(blank=True, max_length=255)),
                ('postal_code', models.CharField(max_length=20)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CaregiverProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('phone', models.CharField(max_length=30)),
                ('city', models.CharField(db_index=True, max_length=100)),
                ('bio', models.TextField(blank=True)),
                ('years_experience', models.PositiveIntegerField(default=0)),
                ('hourly_rate_base', models.DecimalField(decimal_places=2, max_digits=10)),
                ('services_offered', models.JSONField(default=list)),
                ('max_pets', models.PositiveIntegerField(default=1)),
                ('accepts_large_dogs', models.BooleanField(default=False)),
                ('accepts_aggressive', models.BooleanField(default=False)),
                ('verified', models.BooleanField(default=False)),
                ('rating_average', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=3)),
                ('rating_count', models.PositiveIntegerField(default=0)),
                ('gps_radius_km', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.SlugField(unique=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('base_duration_minutes', models.PositiveIntegerField(default=60)),
                ('default_base_price', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('start_datetime', models.DateTimeField(db_index=True)),
                ('end_datetime', models.DateTimeField(db_index=True)),
                ('duration_minutes', models.PositiveIntegerField()),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Pending'),
                            ('accepted', 'Accepted'),
                            ('rejected', 'Rejected'),
                            ('cancelled', 'Cancelled'),
                            ('completed', 'Completed'),
                        ],
                        db_index=True,
                        default='pending',
                        max_length=20,
                    ),
                ),
                ('owner_notes', models.TextField(blank=True)),
                ('caregiver_notes', models.TextField(blank=True)),
                ('price_subtotal', models.DecimalField(decimal_places=2, max_digits=10)),
                ('platform_fee', models.DecimalField(decimal_places=2, max_digits=10)),
                ('caregiver_earnings', models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    'payment_status',
                    models.CharField(
                        choices=[('pending', 'Pending'), ('paid', 'Paid'), ('refunded', 'Refunded')],
                        default='pending',
                        max_length=20,
                    ),
                ),
                (
                    'caregiver',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='bookings',
                        to='marketplace.caregiverprofile',
                    ),
                ),
                (
                    'owner',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='marketplace.ownerprofile'
                    ),
                ),
                ('pet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='marketplace.pet')),
                (
                    'service_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='marketplace.servicetype'
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='CaregiverAvailability',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('weekday', models.PositiveSmallIntegerField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('is_recurring', models.BooleanField(default=True)),
                (
                    'caregiver',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='availabilities',
                        to='marketplace.caregiverprofile',
                    ),
                ),
            ],
            options={'ordering': ['weekday', 'start_time']},
        ),
        migrations.CreateModel(
            name='CaregiverService',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('price_per_unit', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                (
                    'caregiver',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='services',
                        to='marketplace.caregiverprofile',
                    ),
                ),
                (
                    'service_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='caregiver_services',
                        to='marketplace.servicetype',
                    ),
                ),
            ],
            options={'unique_together': {('caregiver', 'service_type')}},
        ),
        migrations.CreateModel(
            name='Pet',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                (
                    'species',
                    models.CharField(
                        choices=[('dog', 'Dog'), ('cat', 'Cat'), ('other', 'Other')],
                        max_length=20,
                    ),
                ),
                ('breed', models.CharField(blank=True, max_length=100)),
                ('sex', models.CharField(choices=[('M', 'Male'), ('F', 'Female')], max_length=1)),
                ('birthdate', models.DateField(blank=True, null=True)),
                ('weight_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('is_neutered', models.BooleanField(default=False)),
                ('medical_notes', models.TextField(blank=True)),
                ('behavior_notes', models.TextField(blank=True)),
                (
                    'owner',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name='pets', to='marketplace.ownerprofile'
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='BookingRecurringRule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('recurrence_type', models.CharField(default='weekly', max_length=50)),
                ('weekdays', django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=list, size=None)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                (
                    'booking',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='recurring_rules',
                        to='marketplace.booking',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='ServiceArea',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('city', models.CharField(db_index=True, max_length=100)),
                ('country', models.CharField(max_length=100)),
                ('geo_center_lat', models.DecimalField(decimal_places=6, max_digits=9)),
                ('geo_center_lng', models.DecimalField(decimal_places=6, max_digits=9)),
                ('radius_km', models.DecimalField(decimal_places=2, max_digits=6)),
                (
                    'caregiver',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='service_areas',
                        to='marketplace.caregiverprofile',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='TimeOff',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_from', models.DateField()),
                ('date_to', models.DateField()),
                ('reason', models.TextField(blank=True)),
                (
                    'caregiver',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='time_off',
                        to='marketplace.caregiverprofile',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='WalkSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('distance_meters', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('route_geojson', models.JSONField(default=list)),
                ('pee_events', models.PositiveIntegerField(default=0)),
                ('poo_events', models.PositiveIntegerField(default=0)),
                ('food_given', models.BooleanField(default=False)),
                ('water_given', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                (
                    'booking',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='walk_sessions',
                        to='marketplace.booking',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='WalkPhoto',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(upload_to='walk_photos/')),
                (
                    'session',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='photos',
                        to='marketplace.walksession',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rating', models.PositiveSmallIntegerField()),
                ('comment', models.TextField(blank=True)),
                (
                    'author',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='reviews_written',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'booking',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='review',
                        to='marketplace.booking',
                    ),
                ),
                (
                    'target_caregiver',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='reviews',
                        to='marketplace.caregiverprofile',
                    ),
                ),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Payout',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='USD', max_length=5)),
                (
                    'status',
                    models.CharField(
                        choices=[('pending', 'Pending'), ('processing', 'Processing'), ('paid', 'Paid'), ('failed', 'Failed')],
                        default='pending',
                        max_length=20,
                    ),
                ),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                (
                    'caregiver',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='payouts',
                        to='marketplace.caregiverprofile',
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='TransactionLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('direction', models.CharField(choices=[('credit', 'Credit'), ('debit', 'Debit')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField()),
                (
                    'booking',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='transactions',
                        to='marketplace.booking',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='transactions',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['status', 'start_datetime'], name='marketplac_status__9fb872_idx'),
        ),
    ]
