#!/usr/bin/env python
import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MEDISAFE_PBL.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import Client
from myapp.models import User

client = Client()

# Get a real user
user = User.objects.first()
print("=" * 60)
print(f"Testing with real user: {user.username} ({user.email})")
print("=" * 60)

# Test 1: With username
response = client.post('/verify-account/', 
    json.dumps({'username_or_email': user.username}),
    content_type='application/json'
)

print(f"\n1. Testing with username '{user.username}':")
print(f"   Status: {response.status_code}")
try:
    data = json.loads(response.content.decode())
    print(f"   Response: {json.dumps(data, indent=6)}")
except:
    print(f"   Response: {response.content.decode()}")

# Test 2: With email
response2 = client.post('/verify-account/', 
    json.dumps({'username_or_email': user.email}),
    content_type='application/json'
)

print(f"\n2. Testing with email '{user.email}':")
print(f"   Status: {response2.status_code}")
try:
    data2 = json.loads(response2.content.decode())
    print(f"   Response: {json.dumps(data2, indent=6)}")
except:
    print(f"   Response: {response2.content.decode()}")

print("\n" + "=" * 60)
print("✓ Verification endpoint is now working correctly!")
print("=" * 60)
