from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from myapp.models import Notification
import os


class Command(BaseCommand):
    help = 'Delete notifications older than 15 days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=15,
            help='Number of days to keep notifications (default: 15)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get notifications older than cutoff date
        old_notifications = Notification.objects.filter(created_at__lt=cutoff_date)
        count = old_notifications.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS(f'No notifications older than {days} days found.'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Would delete {count} notification(s) older than {days} days.'))
            # Show some examples
            for notif in old_notifications[:5]:
                self.stdout.write(f'  - {notif.title} (created: {notif.created_at})')
            if count > 5:
                self.stdout.write(f'  ... and {count - 5} more')
            return
        
        # Delete associated files first
        deleted_files = 0
        for notification in old_notifications:
            if notification.file:
                try:
                    file_path = notification.file.path
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_files += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Could not delete file for notification {notification.notification_id}: {e}'))
        
        # Delete notifications
        old_notifications.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {count} notification(s) older than {days} days. '
                f'Removed {deleted_files} associated file(s).'
            )
        )

