# Liquor Association Membership Management System

Django + PostgreSQL membership portal for applicant registration, KYC upload, admin verification, manual payment proof approval, membership generation, QR verification, reports, and a digital membership card.

## Stack

- Django 5.2
- PostgreSQL 16
- Docker Compose
- Django Admin for operations
- WhiteNoise for static files
- QR code generation for memberships

## Quick Start

1. Install Docker Desktop.
2. Copy `.env.example` to `.env` and update payment/bank details.
3. Start the app:

```bash
docker compose up --build
```

4. Create an admin user:

```bash
docker compose exec web python manage.py createsuperuser
```

5. Open:

- Member portal: `http://localhost:8000`
- Admin panel: `http://localhost:8000/admin/`
- Staff reports: `http://localhost:8000/reports/`

## Core Workflow

1. Applicant creates an account.
2. Applicant submits the membership application and KYC documents.
3. Admin reviews documents in Django Admin.
4. Admin approves the application, which moves it to pending payment.
5. Applicant uploads payment screenshot, UTR number, payment date, and bank name.
6. Admin approves the payment.
7. System generates membership number, QR code, validity, and digital card.

## Production Notes

- Replace `DJANGO_SECRET_KEY`.
- Set `DJANGO_DEBUG=False`.
- Set real `DJANGO_ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- Put uploaded media on durable storage in production.
- Connect SMS/email OTP providers before public launch.
- Use HTTPS at the reverse proxy/load balancer.
- Restrict Django Admin access to staff accounts only.

## Deployment

Render deployment and GitHub Actions CI/CD are documented in [DEPLOYMENT.md](DEPLOYMENT.md).

## Suggested One-Week Build Plan

- Day 1: Confirm fields, status flow, and deploy Docker/Postgres.
- Day 2: Polish applicant form and file validation.
- Day 3: Admin review screens/actions and notifications.
- Day 4: Payment proof workflow and UTR checks.
- Day 5: Card/certificate PDF download and QR verification URL.
- Day 6: Reports, search filters, export.
- Day 7: testing, permissions, deployment, data backup setup.
