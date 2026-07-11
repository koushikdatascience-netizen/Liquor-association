"""Send membership renewal reminder emails to members whose validity is ending soon.

Run daily (e.g. via cron or a scheduled container job):
    python manage.py send_renewal_reminders
    python manage.py send_renewal_reminders --days 30 --dry-run
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from membership.models import Member
from membership.services import notify_member_email_only


class Command(BaseCommand):
    help = "Email members whose membership is due for renewal within the given window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Renewal window in days from today (default: 30).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List recipients without sending emails.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        today = timezone.localdate()
        window_end = today + timedelta(days=days)

        # Active members whose validity falls within [today, today+days]
        members = Member.objects.filter(
            is_active=True,
            valid_till__range=(today, window_end),
        ).select_related("application", "user")

        sent = 0
        for member in members:
            user = member.user
            application = member.application
            subject = f"Membership renewal reminder - {member.membership_number}"
            body = (
                f"Dear {application.full_name},\n\n"
                f"Your membership with {settings.ASSOCIATION_NAME} is due for renewal on "
                f"{member.valid_till:%d %b %Y}.\n\n"
                f"Membership Number: {member.membership_number}\n"
                f"Shop: {application.shop_name}\n\n"
                f"Please complete the renewal payment before the expiry date to avoid interruption "
                f"of member benefits.\n\n"
                f"You can renew from your member dashboard:\n{settings.SITE_URL}\n\n"
                f"Regards,\n{settings.ASSOCIATION_NAME}"
            )
            if dry_run:
                self.stdout.write(f"[dry-run] Would email {user.email} ({member.membership_number})")
                sent += 1
                continue
            notify_member_email_only(user, title=subject, message=body)
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Renewal reminders processed: {sent}"))