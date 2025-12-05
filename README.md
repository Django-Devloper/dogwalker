# PetWalk Marketplace

Production-ready Django 5 / DRF scaffold for a multi-tenant pet care marketplace (walks, sitting, boarding, grooming).

## Getting started

1. Create and activate a Python 3.11 virtualenv.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment template and adjust secrets:
   ```bash
   cp .venv.example .venv
   ```
4. Run migrations and create a superuser:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
5. (Optional) Generate demo data:
   ```bash
   python manage.py generate_dummy_data
   ```
6. Start the server and explore the API docs at `/api/docs/`.

## Highlights
- Token-based auth with owner and caregiver registration flows.
- Rich domain models for bookings, services, availability, walks, reviews, and payouts.
- Commission computation via configurable `PLATFORM_FEE_PERCENT`.
- drf-spectacular for OpenAPI schema at `/api/schema/`.
