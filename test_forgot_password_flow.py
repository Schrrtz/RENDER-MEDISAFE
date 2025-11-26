#!/usr/bin/env python
import os
import sys
import django
import json
from io import BytesIO

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MEDISAFE_PBL.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from myapp.models import User, Notification
from PIL import Image

client = Client()

# Get a real user
user = User.objects.first()
print("=" * 60)
print("TESTING COMPLETE FORGOT PASSWORD FLOW")
print("=" * 60)

# Step 1: Verify account
print(f"\n[STEP 1] Verifying account: {user.username}")
response = client.post('/verify-account/', 
    json.dumps({'username_or_email': user.username}),
    content_type='application/json'
)
print(f"Status: {response.status_code}")
data = json.loads(response.content.decode())
print(f"Account exists: {data.get('exists')}")
print(f"User ID: {data.get('user_id')}")
print(f"Full name: {data.get('full_name')}")

# Step 2: Create a test image
print(f"\n[STEP 2] Creating test image file")
img = Image.new('RGB', (100, 100), color='red')
img_io = BytesIO()
img.save(img_io, format='JPEG')
img_io.seek(0)

# Step 3: Submit forgot password form with file
print(f"\n[STEP 3] Submitting forgot password request with photo")
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

print(f"Status: {response.status_code}")
try:
    data = json.loads(response.content.decode())
    print(f"Response: {json.dumps(data, indent=2)}")
except:
    print(f"Response: {response.content.decode()}")

# Step 4: Verify notification was created
print(f"\n[STEP 4] Checking if notification was created")
notifications = Notification.objects.filter().order_by('-created_at')
if notifications.exists():
    notif = notifications.first()
    print(f"✓ Notification created!")
    print(f"  - notification_id: {notif.notification_id}")
    print(f"  - Type: {notif.notification_type}")
    print(f"  - Recipient: {notif.user.username} (Admin)")
    print(f"  - File present: {bool(notif.file)}")
    if notif.file:
        print(f"  - File name: {notif.file.name}")
        print(f"  - File size: {notif.file.size} bytes")
    print(f"  - Related to user ID: {notif.related_id}")
else:
    print("✗ No notification found")

print("\n" + "=" * 60)
print("✓ FORGOT PASSWORD FLOW TEST COMPLETE!")
print("=" * 60)
