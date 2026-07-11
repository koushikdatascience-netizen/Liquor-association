# Render Deployment and GitHub Actions CI/CD

This project is ready for Docker-based deployment on Render with PostgreSQL.

## 1. Push the Repository to GitHub

Commit and push the project to the GitHub repository connected to Render.

## 2. Create the Render Services

Recommended path:

1. Open Render Dashboard.
2. Click **New +**.
3. Select **Blueprint**.
4. Connect the GitHub repository.
5. Render will detect `render.yaml`.
6. Create the services.

The blueprint creates:

- `liquor-association-web`
- `liquor-association-db`
- `/app/media` persistent disk for uploaded documents and payment screenshots

If you already created only a Render **Web Service**, the PostgreSQL database will not exist automatically. In that case, create it manually:

1. Open Render Dashboard.
2. Click **New +**.
3. Select **PostgreSQL**.
4. Name it `liquor-association-db`.
5. Set database name to `registration`.
6. Set user to `registration`.
7. Create the database.
8. Open the database service after it is ready.
9. Copy the **Internal Database URL**.
10. Open your web service.
11. Go to **Environment**.
12. Add or replace:

```env
DATABASE_URL=<paste Render Internal Database URL here>
```

13. Save changes and run **Manual Deploy > Deploy latest commit**.

## 3. Fill Secret Environment Variables in Render

After the Blueprint is created, open the web service and fill the secret values marked `sync: false`:

```env
PAYMENT_UPI_ID=
PAYMENT_BANK_NAME=
PAYMENT_ACCOUNT_NAME=
PAYMENT_ACCOUNT_NUMBER=
PAYMENT_IFSC=

SMTP_PASSWORD=
SMTP_FROM_EMAIL=
EMAIL_TIMEOUT=10
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
ADMIN_NOTIFICATION_EMAIL=societywelfarewbfllicences@gmail.com

PINBOT_PHONE_NUMBER_ID=
PINBOT_API_KEY=
PINBOT_NOTIFICATION_TEMPLATE_NAME=
WHATSAPP_NOTIFICATIONS_ENABLED=

DJANGO_ADMIN_PASSWORD=
```

For Hostinger SMTP:

```env
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=465
SMTP_USERNAME=wbliquor@snapkey.in
SMTP_PASSWORD=<Hostinger mailbox password>
SMTP_FROM_EMAIL=wbliquor@snapkey.in
SMTP_FROM_NAME=WB Foreign Liquor and IML Licensees
SMTP_USE_SSL=True
EMAIL_USE_SSL=True
EMAIL_USE_TLS=False
EMAIL_TIMEOUT=10
```

For Pinbot WhatsApp templates:

```env
PINBOT_API_BASE_URL=https://partnersv1.pinbot.ai/v3
PINBOT_PHONE_NUMBER_ID=908272842364302
PINBOT_API_KEY=<Pinbot API key>
PINBOT_LANGUAGE_CODE=en
PINBOT_NOTIFICATION_TEMPLATE_NAME=support_request
WHATSAPP_NOTIFICATIONS_ENABLED=True
```

The default notification template payload sends three body text parameters, matching the shared Pinbot sample: association name, a reference, and the message body.

## 4. Add GitHub Actions Secret

In Render:

1. Open `liquor-association-web`.
2. Go to **Settings**.
3. Copy the **Deploy Hook** URL.

In GitHub:

1. Go to repository **Settings**.
2. Open **Secrets and variables > Actions**.
3. Add a repository secret:

```env
RENDER_DEPLOY_HOOK_URL=https://api.render.com/deploy/...
```

## 5. CI/CD Flow

The workflow at `.github/workflows/render-deploy.yml` does this:

1. Runs on pull requests and pushes to `main`.
2. Starts PostgreSQL for CI.
3. Installs Python dependencies.
4. Runs migrations.
5. Runs Django deployment checks.
6. Collects static files.
7. Calls the Render deploy hook only on `main` push.

## 6. Create Production Superuser

If Render Shell is available, you can create an admin manually:

```bash
python manage.py createsuperuser
```

If Render Shell is not available, set these environment variables on the web service and redeploy:

```env
DJANGO_ADMIN_USERNAME=admin
DJANGO_ADMIN_EMAIL=admin@example.com
DJANGO_ADMIN_PASSWORD=Admin@12345
```

On every deploy, the app will create or reset that admin user automatically when `DJANGO_ADMIN_PASSWORD` is present.

## 7. Important Production Notes

- Keep `DJANGO_DEBUG=False`.
- Use a verified Resend sender/domain before sending real emails.
- Uploaded KYC documents and payment screenshots need persistent storage. The included Render disk handles this for the web service.
- For heavy production usage, move media to S3-compatible object storage later.

## Troubleshooting

### `Invalid HTTP_HOST header: 'your-service.onrender.com'`

This means Django blocked the Render domain because it was not in `ALLOWED_HOSTS`.

The project settings already allow Render domains with:

```python
.onrender.com
```

After pulling the latest code, redeploy the web service. If you want to be stricter, set this in Render environment:

```env
DJANGO_ALLOWED_HOSTS=liquor-association.onrender.com
CSRF_TRUSTED_ORIGINS=https://liquor-association.onrender.com
SITE_URL=https://liquor-association.onrender.com
```

### `django.db.utils.OperationalError: [Errno -2] Name or service not known`

This means the deployed Django container cannot resolve the database hostname.

Most common cause: Render has the local Docker Compose database URL:

```env
DATABASE_URL=postgres://registration:registration@db:5432/registration
```

That URL only works on your laptop inside `docker compose`. It does not work on Render because there is no host named `db`.

Fix in Render:

1. Open the Render web service.
2. Go to **Environment**.
3. Check `DATABASE_URL`.
4. If it contains `@db:5432`, delete it.
5. If there is no Render PostgreSQL service, create one from **New + > PostgreSQL**.
6. Add the Render PostgreSQL **Internal Database URL** as `DATABASE_URL`.

If you created the app from `render.yaml` Blueprint, Render should set this automatically from:

```yaml
fromDatabase:
  name: liquor-association-db
  property: connectionString
```

If it did not, open the Render PostgreSQL service, copy its internal connection string, and paste it into the web service as `DATABASE_URL`.

After updating the environment variable, click **Manual Deploy > Deploy latest commit**.
