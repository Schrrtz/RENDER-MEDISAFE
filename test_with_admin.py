import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MEDISAFE_PBL.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from myapp.models import User

# Create an admin user for testing
admin = User.objects.create(
    username='admin_test',
    email='admin@example.com',
    role='admin',
    is_active=True,
    status=True
)
print(f"✓ Created admin user: {admin.username} (ID: {admin.user_id})")

# Now run the forgot password test again
import json
from io import BytesIO
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from myapp.models import Notification
from PIL import Image

client = Client()
user = User.objects.filter(role='patient').first()

print("\n" + "=" * 60)
print("TESTING FORGOT PASSWORD WITH ADMIN USER PRESENT")
print("=" * 60)

# Step 1: Verify account
print(f"\n[STEP 1] Verifying account: {user.username}")
response = client.post('/verify-account/', 
    json.dumps({'username_or_email': user.username}),
    content_type='application/json'
)
data = json.loads(response.content.decode())
print(f"Status: {response.status_code} - Account exists: {data.get('exists')}")

# Step 2: Create test image
print(f"\n[STEP 2] Creating test image")
img = Image.new('RGB', (100, 100), color='blue')
img_io = BytesIO()
img.save(img_io, format='JPEG')
img_io.seek(0)

# Step 3: Submit forgot password with admin present
print(f"\n[STEP 3] Submitting forgot password request")
test_file = SimpleUploadedFile(
    "id_photo.jpg",
    img_io.getvalue(),
    content_type="image/jpeg"
)

response = client.post('/forgot-password/', {
    'username_or_email': user.username,
    'contact_method': 'email',
    'id_photo': test_file
})

data = json.loads(response.content.decode())
print(f"Status: {response.status_code}")
print(f"Success: {data.get('success')}")
print(f"Message: {data.get('message')}")

# Step 4: Check notification
print(f"\n[STEP 4] Checking notifications")
notifs = Notification.objects.filter(notification_type='password_reset').order_by('-created_at')
print(f"Password reset notifications: {notifs.count()}")

if notifs.exists():
    for notif in notifs[:3]:
        print(f"\n  Notification ID: {notif.notification_id}")
        print(f"  To: {notif.user.username} (Admin)")
        print(f"  Subject: {notif.title}")
        print(f"  File: {notif.file.name if notif.file else 'No file'}")
        if notif.file:
            print(f"  File size: {notif.file.size} bytes")

print("\n" + "=" * 60)
print("✓ TEST COMPLETE!")
print("=" * 60)
