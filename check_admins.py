import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MEDISAFE_PBL.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from myapp.models import User

print("=" * 60)
print("CHECKING USER ROLES")
print("=" * 60)

users = User.objects.all()[:10]
for u in users:
    print(f"{u.username}: role={u.role}, is_active={u.is_active}, status={getattr(u, 'status', 'N/A')}")

print(f"\nTotal users: {User.objects.count()}")

# Check for admin users by role
admin_users = User.objects.filter(role='admin')
print(f"\nUsers with role='admin': {admin_users.count()}")
for u in admin_users:
    print(f"  - {u.username} (is_active={u.is_active})")
