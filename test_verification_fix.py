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

client = Client()

# Test verify-account endpoint with correct path
print("=" * 60)
print("Testing /verify-account/ endpoint")
print("=" * 60)

response = client.post('/verify-account/', 
    json.dumps({'username_or_email': 'john_doe'}),
    content_type='application/json'
)

print(f"Status: {response.status_code}")
print(f"Response Content:")
try:
    print(json.dumps(json.loads(response.content.decode()), indent=2))
except:
    print(response.content.decode())

print("\n" + "=" * 60)
print("Testing with email")
print("=" * 60)

response2 = client.post('/verify-account/', 
    json.dumps({'username_or_email': 'testuser@example.com'}),
    content_type='application/json'
)

print(f"Status: {response2.status_code}")
print(f"Response Content:")
try:
    print(json.dumps(json.loads(response2.content.decode()), indent=2))
except:
    print(response2.content.decode())

print("\nTest complete!")
