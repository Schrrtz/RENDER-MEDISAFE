from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from myapp.models import User

class Command(BaseCommand):
    help = 'Rehash all user passwords in the database'

    def handle(self, *args, **options):
        users = User.objects.all()
        updated = 0
        
        for user in users:
            # Skip if password is already hashed
            if not user.password.startswith(('pbkdf2_sha256$', 'bcrypt$', 'argon2')):
                raw_password = user.password
                user.password = make_password(raw_password)
                user.save()
                updated += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully rehashed {updated} passwords')
        )